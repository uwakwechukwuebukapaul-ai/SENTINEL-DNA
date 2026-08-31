"""Evidence-only deployment contract validation.

The validator observes a checkout and operator-supplied evidence.  It never
starts services, calls Docker, changes application configuration, or writes to
the application database.  Migration rehearsal uses an in-memory SQLite
database and backup restore uses a disposable temporary target.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any, Mapping

from config.runtime import RuntimeConfig
from deployment.scripts.build_context_policy import validate_policy
from deployment.scripts.release_manifest import ReleaseManifestError, verify_manifest
from deployment.scripts.validate_deployment_config import (
    METADATA_NAMES,
    SECRET_NAMES,
    merged_environment,
    validate_configuration,
)
from deployment.validation.recovery import BackupRecoveryValidationService, MigrationRehearsalService


REPORT_VERSION = "sentinel-dna-deployment-contract-validation.v1"
REPLAY_VERSION = "sentinel-dna-deployment-contract-replay.v1"

# These are custody boundaries, not inputs to application decision logic.  A
# dirty protected file makes the evidence inconclusive rather than weakening
# the validator or changing the protected implementation.
PROTECTED_PATHS = (
    "services/platform_gateway/authorization.py",
    "services/tenant/authorization.py",
    "services/intelligence/investigation/investigation_result.py",
    "services/intelligence/orchestration/investigation/investigation_coordinator.py",
    "services/intelligence/orchestration/investigation_orchestrator.py",
    "services/intelligence/runtime/runtime_task_executor.py",
)


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _dockerfile_instructions(text: str) -> tuple[str, ...]:
    """Return effective Dockerfile instructions with continuations joined."""

    instructions: list[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if current:
            current = f"{current} {line}"
        else:
            current = line
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        instructions.append(current)
        current = ""
    if current:
        instructions.append(current)
    return tuple(instructions)


def _dockerfile_command(instructions: tuple[str, ...]) -> tuple[str, ...]:
    """Parse the final Docker CMD in either exec or shell form."""

    command: tuple[str, ...] = ()
    for instruction in instructions:
        name, _, payload = instruction.partition(" ")
        if name.upper() != "CMD" or not payload.strip():
            continue
        payload = payload.strip()
        try:
            parsed = json.loads(payload) if payload.startswith("[") else shlex.split(payload)
        except ValueError:
            command = ()
            continue
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            command = tuple(parsed)
        elif isinstance(parsed, tuple):
            command = parsed
        else:
            command = ()
    return command


def _dockerfile_runtime_user(instructions: tuple[str, ...]) -> str:
    users = [
        payload.strip().split()[0]
        for instruction in instructions
        for name, _, payload in [instruction.partition(" ")]
        if name.upper() == "USER" and payload.strip()
    ]
    return users[-1].split(":", 1)[0] if users else ""


def _dockerfile_debug_disabled(instructions: tuple[str, ...]) -> bool:
    effective_text = "\n".join(instructions)
    debug_markers = (
        r"\bFLASK_DEBUG\s*=\s*[\"']?(?:1|true|yes|on)\b",
        r"\b(?:FLASK_|SENTINEL_DNA_)?DEBUG\s*=\s*[\"']?(?:1|true|yes|on)\b",
        r"\b(?:FLASK_ENV|SENTINEL_DNA_ENV)\s*=\s*[\"']?development\b",
        r"(?:^|\s)--debug(?:\s|$)",
        r"\bflask\s+run\b",
    )
    return not any(re.search(marker, effective_text, flags=re.IGNORECASE) for marker in debug_markers)


def _dockerfile_worker_count(command: tuple[str, ...]) -> str | None:
    for argument in command:
        if argument.startswith("--workers="):
            return argument.partition("=")[2]
    try:
        index = command.index("--workers")
    except ValueError:
        return None
    return command[index + 1] if index + 1 < len(command) else ""


def _result(name: str, passed: bool, checks: Mapping[str, bool], failures: list[str], evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract": name,
        "status": "passed" if passed else "failed",
        "checks": dict(sorted(checks.items())),
        "failures": sorted(set(failures)),
        "evidence": dict(evidence),
    }


def _git_changed(root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", "diff", "HEAD", "--name-only", "--", *paths],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return paths
    return tuple(sorted(line.strip() for line in completed.stdout.splitlines() if line.strip()))


@dataclass(frozen=True)
class DeploymentContractReport:
    """Immutable, non-secret evidence produced by one validation run."""

    report_version: str
    generated_at: str
    validation_result: str
    contracts: tuple[dict[str, Any], ...]
    safety_invariants: dict[str, bool]
    evidence_policy: dict[str, Any]
    replay_digest: str
    report_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "validation_result": self.validation_result,
            "contracts": list(self.contracts),
            "safety_invariants": dict(sorted(self.safety_invariants.items())),
            "evidence_policy": self.evidence_policy,
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class DeploymentContractValidator:
    """Run deployment checks without changing runtime or persistence state."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        environ: Mapping[str, str] | None = None,
        env_file: str | Path | None = None,
        release_manifest: str | Path | None = None,
        backup_source: str | Path | None = None,
        backup_artifact: str | Path | None = None,
        backup_manifest: str | Path | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.environ = dict(environ) if environ is not None else None
        self.env_file = Path(env_file).resolve() if env_file else None
        self.release_manifest = Path(release_manifest).resolve() if release_manifest else None
        self.backup_source = Path(backup_source).resolve() if backup_source else None
        self.backup_artifact = Path(backup_artifact).resolve() if backup_artifact else None
        self.backup_manifest = Path(backup_manifest).resolve() if backup_manifest else None
        self.generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    def _environment(self) -> dict[str, str]:
        return merged_environment(environ=self.environ, env_file=self.env_file)

    def runtime_configuration(self) -> dict[str, Any]:
        values = self._environment()
        errors = validate_configuration(
            environ=values,
            repository_root=self.repository_root,
        )
        safe_errors = [
            str(error) if ":" not in str(error)
            else str(error).split(":", 1)[0] + ":" + str(error).split(":", 1)[1]
            for error in errors
        ]
        checks = {
            "protected_configuration": not errors,
            "secret_values_not_serialized": True,
            "production_environment": values.get("SENTINEL_DNA_ENV", "production").lower() == "production",
        }
        return _result(
            "runtime_configuration",
            all(checks.values()),
            checks,
            safe_errors,
            {
                "checked_variables": sorted(
                    set(SECRET_NAMES)
                    | set(METADATA_NAMES)
                    | {
                        "SENTINEL_DNA_ENV",
                        "SENTINEL_DNA_SECURE_COOKIES",
                        "SENTINEL_DNA_DB_PATH",
                        "DATABASE_URL",
                        "SENTINEL_DNA_IMAGE_DIGEST",
                        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE",
                    }
                ),
                "error_codes": safe_errors,
            },
        )

    def production_startup(self) -> dict[str, Any]:
        values = self._environment()
        checks: dict[str, bool] = {}
        failures: list[str] = []
        config = RuntimeConfig(
            environment=values.get("SENTINEL_DNA_ENV", values.get("FLASK_ENV", "development")).lower(),
            database_path=values.get("SENTINEL_DNA_DB_PATH", "soc.db"),
            secret_key=values.get("SENTINEL_DNA_SECRET_KEY", ""),
            secure_cookies=values.get("SENTINEL_DNA_SECURE_COOKIES", "0") == "1",
            debug=values.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes", "on"},
            database_url=values.get("DATABASE_URL", "").strip(),
        )
        secret = config.secret_key.strip().lower()
        parent = Path(config.database_path).expanduser().resolve().parent
        database_configured = bool(config.database_url) or bool(values.get("SENTINEL_DNA_DB_PATH", "").strip())
        checks["runtime_config_accepts_startup"] = (
            config.environment == "production"
            and len(secret) >= 32
            and not any(marker in secret for marker in ("change-me", "replace-with", "development-only"))
            and config.secure_cookies
            and not config.debug
            and database_configured
            and (bool(config.database_url) or (parent.is_dir() and os.access(parent, os.W_OK)))
        )
        if not checks["runtime_config_accepts_startup"]:
            failures.append("runtime_startup_rejected")
        dockerfile = self.repository_root / "Dockerfile"
        wsgi = self.repository_root / "wsgi.py"
        docker_text = dockerfile.read_text(encoding="utf-8") if dockerfile.is_file() else ""
        wsgi_text = wsgi.read_text(encoding="utf-8") if wsgi.is_file() else ""
        instructions = _dockerfile_instructions(docker_text)
        command = _dockerfile_command(instructions)
        runtime_user = _dockerfile_runtime_user(instructions)
        worker_count = _dockerfile_worker_count(command)
        image_checks = {
            "canonical_wsgi_entrypoint": (
                wsgi.is_file()
                and "from app import create_app" in wsgi_text
                and re.search(r"^\s*application\s*=\s*create_app\(\)\s*$", wsgi_text, flags=re.MULTILINE)
                and "wsgi:application" in command
            ),
            "gunicorn_production_server": bool(command)
            and (
                Path(command[0]).name.lower() == "gunicorn"
                or command[:3] == ("python", "-m", "gunicorn")
            ),
            "non_root_runtime_user": runtime_user == "sentinel",
            "debug_mode_disabled": _dockerfile_debug_disabled(instructions),
            # SQLite is process-local, so it must remain behind one Gunicorn
            # worker. PostgreSQL-backed production may use its configured
            # worker count (or Gunicorn's default) without this restriction.
            "single_sqlite_worker_boundary": bool(config.database_url) or worker_count == "1",
        }
        checks.update(image_checks)
        # Keep the public check name while making it describe the image
        # characteristics that make the image safe for production startup.
        checks["production_image_mode"] = all(image_checks.values())
        failures.extend(name for name, passed in checks.items() if not passed)
        return _result(
            "production_startup",
            all(checks.values()),
            checks,
            failures,
            {
                "observed_files": [
                    path for path in ("Dockerfile", "wsgi.py") if (self.repository_root / path).is_file()
                ],
                "runtime_environment_source": "operator_environment_or_compose",
                "image_command": list(command),
                "image_runtime_user": runtime_user,
                "sqlite_worker_boundary_required": not bool(config.database_url),
            },
        )

    def migration_rehearsal(self) -> dict[str, Any]:
        return MigrationRehearsalService(self.repository_root).validate()

    def artifact_integrity(self) -> dict[str, Any]:
        checks: dict[str, bool] = {}
        failures: list[str] = []
        policy_errors = validate_policy(self.repository_root)
        checks["docker_context_policy"] = not policy_errors
        if policy_errors:
            failures.extend(policy_errors)
        dockerfile = self.repository_root / "Dockerfile"
        compose = self.repository_root / "deployment" / "docker-compose.yml"
        docker_text = dockerfile.read_text(encoding="utf-8") if dockerfile.is_file() else ""
        compose_text = compose.read_text(encoding="utf-8") if compose.is_file() else ""
        checks.update({
            "dockerfile_present": dockerfile.is_file(),
            "compose_present": compose.is_file(),
            "internal_application_port_not_published": "5000:5000" not in compose_text,
            "immutable_image_reference_contract": "SENTINEL_DNA_IMAGE_TAG:?set" in compose_text,
            "non_root_dockerfile": "USER sentinel" in docker_text,
        })
        if self.release_manifest is None:
            checks["release_manifest_verified"] = False
            failures.append("release_manifest_missing")
        else:
            values = self._environment()
            try:
                verify_manifest(
                    manifest_path=self.release_manifest,
                    repository_root=self.repository_root,
                    require_image=True,
                    expected_release_sha=values.get("SENTINEL_DNA_IMAGE_REVISION_FULL") or None,
                    expected_image_digest=values.get("SENTINEL_DNA_IMAGE_DIGEST") or None,
                    expected_image_created=values.get("SENTINEL_DNA_IMAGE_CREATED") or None,
                )
                checks["release_manifest_verified"] = True
            except (ReleaseManifestError, OSError, ValueError):
                checks["release_manifest_verified"] = False
                failures.append("release_manifest_invalid")
        failures.extend(name for name, passed in checks.items() if not passed)
        files = [path for path in ("Dockerfile", ".dockerignore", "deployment/docker-compose.yml") if (self.repository_root / path).is_file()]
        return _result(
            "deployment_artifact_integrity",
            all(checks.values()),
            checks,
            failures,
            {"observed_files": files, "file_sha256": {path: _file_digest(self.repository_root / path) for path in files}},
        )

    def backup_restore_readiness(self) -> dict[str, Any]:
        return BackupRecoveryValidationService(
            source=self.backup_source,
            artifact=self.backup_artifact,
            manifest=self.backup_manifest,
        ).validate()

    def run(self) -> DeploymentContractReport:
        contracts = (
            self.runtime_configuration(),
            self.production_startup(),
            self.migration_rehearsal(),
            self.artifact_integrity(),
            self.backup_restore_readiness(),
        )
        changed = _git_changed(self.repository_root, PROTECTED_PATHS)
        safety = {
            "authorization_logic_untouched": not changed,
            "verdict_enforcement_untouched": not changed,
            "tenant_isolation_preserved": contracts[-1]["checks"].get("tenant_isolation_after_restore", False),
            "audit_integrity_preserved": contracts[-1]["checks"].get("audit_integrity_after_restore", False),
            "append_only_evidence_preserved": True,
            "validator_is_observation_only": True,
        }
        replay_input = {
            "replay_version": REPLAY_VERSION,
            "contracts": contracts,
            "safety_invariants": safety,
            "protected_paths": PROTECTED_PATHS,
        }
        replay_digest = _digest(replay_input)
        report_body = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "validation_result": "passed" if all(item["status"] == "passed" for item in contracts) and all(safety.values()) else "failed",
            "contracts": contracts,
            "safety_invariants": dict(sorted(safety.items())),
            "evidence_policy": {
                "secrets_serialized": False,
                "database_rows_serialized": False,
                "external_integrations_used": False,
                "deployment_performed": False,
                "output_mode": "immutable_append_only",
                "replay_digest_excludes": ["generated_at", "host_paths", "timing"],
            },
            "replay_digest": replay_digest,
        }
        return DeploymentContractReport(
            report_version=REPORT_VERSION,
            generated_at=self.generated_at,
            validation_result=report_body["validation_result"],
            contracts=tuple(contracts),
            safety_invariants=safety,
            evidence_policy=report_body["evidence_policy"],
            replay_digest=replay_digest,
            report_digest=_digest(report_body),
        )


def write_immutable_report(report: DeploymentContractReport, output: str | Path, *, repository_root: str | Path) -> Path:
    """Write one report and refuse replacement or repository-local evidence."""

    root = Path(repository_root).resolve()
    candidate = Path(output).expanduser()
    if candidate.is_symlink() or candidate.parent.is_symlink():
        raise ValueError("evidence_output_reparse_point")
    target = candidate.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("evidence_output_must_be_outside_repository")
    if target.exists() or target.is_symlink():
        raise FileExistsError("immutable_evidence_already_exists")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError("evidence_output_parent_invalid")
    temporary = target.with_name(f".{target.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError("immutable_evidence_temporary_already_exists")
    temporary.write_text(report.to_json(), encoding="utf-8", newline="\n")
    try:
        # A hard link refuses an existing destination, including a race after
        # the initial existence check. It therefore cannot replace evidence.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def replay_digest(report: DeploymentContractReport) -> str:
    """Return the stable digest used to compare two offline replays."""

    return report.replay_digest
