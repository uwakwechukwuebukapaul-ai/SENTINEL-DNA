"""Evidence-only validation for a disposable PostgreSQL rehearsal.

This validator deliberately does not import a PostgreSQL driver or open a
socket.  A separately authorized rehearsal may provide a bounded JSON evidence
manifest; this module validates that manifest without accepting credentials,
customer data, or claims about a production database.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


REPORT_VERSION = "sentinel-dna-postgres-rehearsal-validation.v1"
REPLAY_VERSION = "sentinel-dna-postgres-rehearsal-replay.v1"
REQUIRED_CHECKS = (
    "migration_ordering",
    "schema_compatibility",
    "migration_success",
    "rollback_capability",
    "tenant_isolation_preservation",
    "evidence_preservation",
    "provenance_preservation",
    "audit_integrity_preservation",
    "investigation_record_preservation",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode("utf-8")).hexdigest()


class PostgresRehearsalValidator:
    """Validate operator-supplied disposable PostgreSQL evidence only."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        evidence_path: str | Path | None = None,
        evidence: Mapping[str, Any] | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.evidence_path = Path(evidence_path).resolve() if evidence_path else None
        self.evidence = dict(evidence) if evidence is not None else None
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    def _load(self) -> tuple[dict[str, Any], str | None]:
        if self.evidence is not None:
            return dict(self.evidence), None
        if self.evidence_path is None:
            return {}, "evidence_not_supplied"
        try:
            value = json.loads(self.evidence_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            return {}, "evidence_unavailable_or_invalid"
        if not isinstance(value, dict):
            return {}, "invalid_evidence_shape"
        return value, None

    @staticmethod
    def _bounded_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
        checks = value.get("checks")
        checks = checks if isinstance(checks, dict) else {}
        return {
            "database_engine": value.get("database_engine"),
            "rehearsal_scope": value.get("rehearsal_scope"),
            "credentials_used": value.get("credentials_used", False),
            "external_connections": value.get("external_connections", False),
            "customer_data_used": value.get("customer_data_used", False),
            "migration_versions": value.get("migration_versions", []),
            "checks": {name: checks.get(name) is True for name in REQUIRED_CHECKS},
            "record_counts": value.get("record_counts", {}),
            "tenant_ids": value.get("tenant_ids", []),
            "provenance_digest": value.get("provenance_digest", ""),
            "audit_digest": value.get("audit_digest", ""),
            "investigation_digest": value.get("investigation_digest", ""),
        }

    def run(self) -> dict[str, Any]:
        raw, load_error = self._load()
        evidence = self._bounded_evidence(raw)
        supplied_checks = evidence["checks"]
        scope_checks = {
            "postgresql_engine_declared": evidence["database_engine"] == "postgresql",
            "disposable_scope_declared": evidence["rehearsal_scope"] == "disposable",
            "no_credentials_used": evidence["credentials_used"] is False,
            "no_external_connections": evidence["external_connections"] is False,
            "no_customer_data_used": evidence["customer_data_used"] is False,
        }
        checks = {**scope_checks, **supplied_checks}
        pending_checks = list(REQUIRED_CHECKS) if load_error else [name for name in REQUIRED_CHECKS if name not in raw.get("checks", {})]
        failures = [name for name, passed in checks.items() if not passed and name not in pending_checks]
        blockers: list[str] = []
        if load_error:
            blockers.append(f"POSTGRES-REHEARSAL:{load_error}")
        blockers.extend(f"POSTGRES-REHEARSAL:{name}" for name in failures)
        blockers.extend(f"POSTGRES-REHEARSAL:PENDING:{name}" for name in pending_checks)
        result = "passed" if not blockers else ("blocked" if load_error or pending_checks else "failed")
        bounded = {
            **evidence,
            "evidence_path_supplied": self.evidence_path is not None or self.evidence is not None,
            "repository_root_recorded": True,
            "secrets_serialized": False,
            "production_database_touched": False,
        }
        stable = {
            "replay_version": REPLAY_VERSION,
            "checks": checks,
            "pending_checks": pending_checks,
            "failures": sorted(failures),
            "scope": {
                "database_engine": evidence["database_engine"],
                "rehearsal_scope": evidence["rehearsal_scope"],
                "credentials_used": False,
                "external_connections": False,
                "customer_data_used": False,
            },
            "migration_versions": evidence["migration_versions"],
            "provenance_digest": evidence["provenance_digest"],
            "audit_digest": evidence["audit_digest"],
            "investigation_digest": evidence["investigation_digest"],
        }
        replay = _digest(stable)
        body = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "validation_result": result,
            "checks": checks,
            "pending_checks": pending_checks,
            "failures": sorted(failures),
            "blockers": sorted(set(blockers)),
            "warnings": [
                "postgres_rehearsal_requires_separately_authorized_disposable_database_evidence",
                "postgres_rehearsal_validator_does_not_open_connections_or_read_credentials",
            ],
            "evidence": bounded,
            "replay_digest": replay,
        }
        return {**body, "report_digest": _digest(body)}


PostgreSQLRehearsalValidator = PostgresRehearsalValidator

__all__ = [
    "PostgresRehearsalValidator",
    "PostgreSQLRehearsalValidator",
    "REQUIRED_CHECKS",
]
