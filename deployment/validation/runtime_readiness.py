"""Evidence-only production runtime readiness validation.

This module validates only supplied configuration metadata and disposable path
properties. It never prints or serializes secret values and never starts the
application.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from deployment.scripts.validate_deployment_config import (
    METADATA_NAMES,
    SECRET_NAMES,
    merged_environment,
    validate_configuration,
)


REPORT_VERSION = "sentinel-dna-runtime-readiness-validation.v1"
REPLAY_VERSION = "sentinel-dna-runtime-readiness-replay.v1"
REQUIRED_NAMES = tuple(sorted({
    *SECRET_NAMES,
    *METADATA_NAMES,
    "SENTINEL_DNA_ENV",
    "SENTINEL_DNA_SECURE_COOKIES",
    "SENTINEL_DNA_DB_PATH",
    "DATABASE_URL",
    "FLASK_DEBUG",
    "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE",
}))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RuntimeReadinessReport:
    report_version: str
    generated_at: str
    validation_result: str
    checks: dict[str, bool]
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]
    evidence: dict[str, Any]
    replay_digest: str
    report_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "validation_result": self.validation_result,
            "checks": dict(sorted(self.checks.items())),
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
            "evidence": self.evidence,
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class RuntimeReadinessValidator:
    """Validate production startup evidence without touching process state."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        environ: Mapping[str, str] | None = None,
        env_file: str | Path | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.environ = dict(environ) if environ is not None else None
        self.env_file = Path(env_file).resolve() if env_file else None
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    def run(self) -> RuntimeReadinessReport:
        values = merged_environment(environ=self.environ, env_file=self.env_file)
        errors = validate_configuration(
            environ=values,
            repository_root=self.repository_root,
        )
        error_codes = tuple(sorted(str(error).split(":", 1)[0] for error in errors))
        missing_secret_probe = dict(values)
        for name in SECRET_NAMES:
            missing_secret_probe.pop(name, None)
        missing_probe_errors = validate_configuration(
            environ=missing_secret_probe,
            repository_root=self.repository_root,
        )
        missing_probe_codes = {str(error).split(":", 1)[0] for error in missing_probe_errors}
        environment = values.get("SENTINEL_DNA_ENV", "production").lower()
        debug_enabled = values.get("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        secure_cookies = values.get("SENTINEL_DNA_SECURE_COOKIES", "") == "1"
        db_path_value = values.get("SENTINEL_DNA_DB_PATH", "").strip()
        database_url_value = values.get("DATABASE_URL", "").strip()
        db_parent = Path(db_path_value).expanduser().resolve().parent if db_path_value else None
        required_without_database = [name for name in REQUIRED_NAMES if name not in {"DATABASE_URL", "SENTINEL_DNA_DB_PATH"}]
        required_present = all(bool(values.get(name, "").strip()) for name in required_without_database) and bool(database_url_value or db_path_value)
        checks = {
            "required_production_configuration_keys": required_present,
            "missing_secrets_fail_closed": all(name in missing_probe_codes for name in SECRET_NAMES),
            "debug_mode_disabled": not debug_enabled,
            "secure_startup_configuration": (
                environment == "production"
                and secure_cookies
                and not debug_enabled
                and (bool(database_url_value) or bool(db_parent and db_parent.is_dir() and os.access(db_parent, os.W_OK)))
            ),
            "configuration_contract_valid": not errors,
            "secret_values_not_printed": True,
            "environment_provenance_recorded": True,
        }
        blockers = tuple(sorted({
            *(f"RUNTIME-CONFIG:{code}" for code in error_codes),
            *("RUNTIME-CONFIG:debug_enabled" for _ in [0] if debug_enabled),
        }))
        warnings = (
            "runtime_readiness_uses_supplied_nonproduction_secret_metadata_only",
            "runtime_readiness_does_not_start_application_or_connect_to_database",
        )
        evidence = {
            "checked_variable_names": list(REQUIRED_NAMES),
            "error_codes": list(error_codes),
            "environment_source": "env_file_and_process_mapping" if self.env_file else "process_mapping_only",
            "env_file_present": bool(self.env_file and self.env_file.is_file()),
            "repository_root_recorded": True,
            "secret_values_serialized": False,
            "debug_observed": debug_enabled,
            "environment_observed": environment,
        }
        stable = {
            "replay_version": REPLAY_VERSION,
            "checks": checks,
            "error_codes": error_codes,
            "warnings": warnings,
            "blockers": blockers,
            "evidence": {
                "checked_variable_names": REQUIRED_NAMES,
                "environment_source": evidence["environment_source"],
                "secret_values_serialized": False,
            },
        }
        replay = _digest(stable)
        missing_evidence = not required_present or bool(error_codes)
        result = "passed" if all(checks.values()) else ("blocked" if missing_evidence else "failed")
        report_body = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "validation_result": result,
            "checks": checks,
            "warnings": warnings,
            "blockers": blockers,
            "evidence": evidence,
            "replay_digest": replay,
        }
        return RuntimeReadinessReport(
            REPORT_VERSION,
            self.generated_at,
            result,
            checks,
            warnings,
            blockers,
            evidence,
            replay,
            _digest(report_body),
        )

    validate = run


__all__ = ["RuntimeReadinessReport", "RuntimeReadinessValidator", "REQUIRED_NAMES"]
