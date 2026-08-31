"""Start and validate the protected production Compose runtime.

The command consumes an operator-provided environment file outside the
repository. It never prints secret values, Compose logs, or database URLs.
The resulting JSON is bounded runtime evidence; use ``--evidence-output`` to
write it once to an external evidence directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deployment" / "docker-compose.yml"
REQUIRED_COMPOSE_ENV = (
    "SENTINEL_DNA_SECRET_KEY",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "SENTINEL_DNA_IMAGE_TAG",
    "SENTINEL_DNA_IMAGE_REVISION",
    "SENTINEL_DNA_IMAGE_REVISION_FULL",
    "SENTINEL_DNA_IMAGE_CREATED",
    "SENTINEL_DNA_IMAGE_DIGEST",
    "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE",
)
CONTROLLED_ENVIRONMENT_NAMES = frozenset(
    {
        "SENTINEL_DNA_ENV",
        "SENTINEL_DNA_SECRET_KEY",
        "POSTGRES_PASSWORD",
        "SENTINEL_DNA_IMAGE_TAG",
        "SENTINEL_DNA_IMAGE_REVISION",
        "SENTINEL_DNA_IMAGE_REVISION_FULL",
        "SENTINEL_DNA_IMAGE_CREATED",
        "SENTINEL_DNA_IMAGE_DIGEST",
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE",
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH",
        "SENTINEL_DNA_TLS_DIR",
        "SENTINEL_DNA_SECURE_COOKIES",
        "SENTINEL_DNA_DB_PATH",
        "DATABASE_URL",
        "SENTINEL_DNA_IMAGE_SOURCE",
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
        "COMPOSE_PROFILES",
        "COMPOSE_ENV_FILES",
        "DOCKER_CONTEXT",
        "DOCKER_HOST",
    }
)


def _external_file(path: Path, *, label: str) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        raise ValueError(f"{label}_must_be_absolute")
    if expanded.is_symlink():
        raise ValueError(f"{label}_unavailable")
    candidate = expanded.resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError(f"{label}_must_be_outside_repository")
    if not candidate.is_file():
        raise ValueError(f"{label}_unavailable")
    return candidate


def _external_output(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        raise ValueError("evidence_output_must_be_absolute")
    if expanded.is_symlink():
        raise ValueError("evidence_output_parent_invalid")
    if expanded.parent.is_symlink():
        raise ValueError("evidence_output_parent_invalid")
    candidate = expanded.resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("evidence_output_must_be_outside_repository")
    if candidate.exists():
        raise FileExistsError("evidence_output_already_exists")
    if candidate.parent.is_symlink() or not candidate.parent.is_dir():
        raise ValueError("evidence_output_parent_invalid")
    return candidate


def _sanitized_process_environment() -> dict[str, str]:
    """Prevent inherited deployment values from overriding the protected file."""
    environment = dict(os.environ)
    for name in CONTROLLED_ENVIRONMENT_NAMES:
        environment.pop(name, None)
    return environment


def _write_evidence(report: dict[str, Any], output: Path) -> Path:
    target = _external_output(output)
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            descriptor = -1
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, target)
    except OSError:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def _run(
    command: Sequence[str],
    *,
    timeout: int = 300,
) -> tuple[bool, str]:
    """Run a Docker command without exposing its output."""
    try:
        result = subprocess.run(
            list(command),
            cwd=ROOT,
            env=_sanitized_process_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, "command_unavailable_or_timeout"
    return result.returncode == 0, "ok" if result.returncode == 0 else "command_failed"


def _safe_json(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _runtime_probe() -> str:
    return (
        "import json, os, urllib.request\n"
        "from database.connection import database\n"
        "if getattr(database, 'backend_name', None) != 'postgresql':\n"
        "    raise SystemExit('non_postgresql_backend')\n"
        "if not database.health_check():\n"
        "    raise SystemExit('postgresql_health_check_failed')\n"
        "def probe(path):\n"
        "    with urllib.request.urlopen('http://127.0.0.1:5000' + path, timeout=5) as response:\n"
        "        return response.status, json.loads(response.read().decode('utf-8'))\n"
        "health_status, health = probe('/health')\n"
        "ready_status, ready = probe('/ready')\n"
        "if health_status != 200 or ready_status != 200:\n"
        "    raise SystemExit('health_or_readiness_failed')\n"
        "print(json.dumps({'backend': database.backend_name, 'health_status': health_status, 'health': health, 'ready_status': ready_status, 'ready': ready, 'uid': os.getuid()}))"
    )


def validate_runtime(
    *,
    env_file: Path,
    project_name: str,
    docker_executable: str = "docker",
    wait_seconds: int = 90,
    cleanup: bool = False,
) -> dict[str, Any]:
    """Run the bounded production startup and return redacted evidence."""
    env_path = _external_file(env_file, label="env_file")
    if not COMPOSE.is_file():
        raise FileNotFoundError("production_compose_missing")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from deployment.scripts.validate_deployment_config import validate_configuration

    # The protected file is the authority for deployment configuration. Do
    # not let an inherited shell value, such as a stale image revision,
    # override it during preflight or Compose interpolation.
    config_errors = validate_configuration(
        environ={},
        env_file=env_path,
        repository_root=ROOT,
        require_postgresql=True,
    )
    checks = {name: False for name in (
        "configuration_preflight",
        "compose_config",
        "postgres_healthy",
        "migration_completed",
        "gunicorn_started",
        "postgresql_connection",
        "health_endpoint",
        "readiness_endpoint",
        "no_sqlite_fallback",
        "non_root_runtime",
    )}
    evidence: dict[str, Any] = {
        "compose_file": "deployment/docker-compose.yml",
        "env_file_name": env_path.name,
        "project_name": project_name,
        "required_secret_names": ["SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"],
        "required_runtime_names": list(REQUIRED_COMPOSE_ENV),
        "secret_values_serialized": False,
        "database_url_serialized": False,
        "config_error_codes": [str(error).split(":", 1)[0] for error in config_errors],
    }
    failures: list[str] = []
    if config_errors:
        failures.append("configuration_preflight")
        evidence["failure_reason"] = "protected_configuration_invalid"
        report = _report(checks, failures, evidence)
        if cleanup:
            _run(_compose(docker_executable, project_name, env_path) + ["down"], timeout=120)
        return report
    checks["configuration_preflight"] = True

    compose = _compose(docker_executable, project_name, env_path)
    ok, reason = _run(compose + ["config", "--quiet"])
    checks["compose_config"] = ok
    evidence["compose_config_status"] = reason
    if not ok:
        failures.append("compose_config")
        return _finish(report=_report(checks, failures, evidence), compose=compose, cleanup=cleanup)

    ok, reason = _run(compose + ["up", "-d", "postgres", "redis"])
    checks["postgres_healthy"] = ok
    evidence["dependencies_start_status"] = reason
    if not ok:
        failures.append("postgres_healthy")
        return _finish(report=_report(checks, failures, evidence), compose=compose, cleanup=cleanup)

    ok, reason = _run(compose + ["run", "--rm", "--build", "migration"])
    checks["migration_completed"] = ok
    evidence["migration_status"] = reason
    if not ok:
        failures.append("migration_completed")
        return _finish(report=_report(checks, failures, evidence), compose=compose, cleanup=cleanup)

    ok, reason = _run(compose + ["up", "-d", "--build", "app"])
    evidence["app_start_status"] = reason
    if not ok:
        failures.append("gunicorn_started")
        return _finish(report=_report(checks, failures, evidence), compose=compose, cleanup=cleanup)

    deadline = time.monotonic() + max(1, wait_seconds)
    probe_payload: dict[str, Any] | None = None
    last_reason = "not_attempted"
    while time.monotonic() < deadline:
        ok, last_reason = _run(compose + ["exec", "-T", "app", "python", "-c", _runtime_probe()], timeout=20)
        if ok:
            # Re-run with captured output only after the command has succeeded;
            # this output is application-generated bounded JSON, not logs.
            result = subprocess.run(
                compose + ["exec", "-T", "app", "python", "-c", _runtime_probe()],
                cwd=ROOT,
                env=_sanitized_process_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=20,
            )
            probe_payload = _safe_json(result.stdout.strip()) if result.returncode == 0 else None
            if probe_payload is not None:
                break
        time.sleep(2)
    evidence["runtime_probe_status"] = last_reason if probe_payload is None else "ok"
    if probe_payload is None:
        failures.extend(("gunicorn_started", "postgresql_connection", "health_endpoint", "readiness_endpoint", "no_sqlite_fallback"))
        return _finish(report=_report(checks, sorted(set(failures)), evidence), compose=compose, cleanup=cleanup)

    checks["gunicorn_started"] = True
    checks["postgresql_connection"] = probe_payload.get("backend") == "postgresql" and probe_payload.get("health", {}).get("database") == "ok"
    checks["health_endpoint"] = probe_payload.get("health_status") == 200
    checks["readiness_endpoint"] = probe_payload.get("ready_status") == 200
    checks["no_sqlite_fallback"] = probe_payload.get("backend") == "postgresql"
    checks["non_root_runtime"] = isinstance(probe_payload.get("uid"), int) and probe_payload["uid"] != 0
    evidence["backend_observed"] = probe_payload.get("backend")
    evidence["health_response"] = probe_payload.get("health")
    evidence["readiness_response"] = probe_payload.get("ready")
    evidence["runtime_uid"] = probe_payload.get("uid")
    failures.extend(name for name, passed in checks.items() if not passed)
    return _finish(report=_report(checks, sorted(set(failures)), evidence), compose=compose, cleanup=cleanup)


def _compose(docker: str, project: str, env_file: Path) -> list[str]:
    return [docker, "compose", "--project-name", project, "--env-file", str(env_file), "--file", str(COMPOSE)]


def _finish(*, report: dict[str, Any], compose: Sequence[str], cleanup: bool) -> dict[str, Any]:
    if cleanup:
        ok, reason = _run(list(compose) + ["down"], timeout=120)
        report["evidence"]["cleanup_status"] = reason if ok else "cleanup_failed"
    return report


def _report(checks: dict[str, bool], failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_version": "sentinel-dna-production-runtime-validation.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "validation_result": "passed" if not failures and all(checks.values()) else "failed",
        "checks": dict(sorted(checks.items())),
        "failures": sorted(set(failures)),
        "evidence": evidence,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True, type=Path, help="external protected environment file")
    parser.add_argument("--project-name", default="sentinel-dna-production-validation")
    parser.add_argument("--docker-executable", default="docker")
    parser.add_argument("--wait-seconds", type=int, default=90)
    parser.add_argument("--cleanup", action="store_true", help="remove validation containers and networks after the run")
    parser.add_argument("--evidence-output", type=Path, help="write immutable redacted evidence outside the repository")
    args = parser.parse_args(argv)
    try:
        report = validate_runtime(
            env_file=args.env_file,
            project_name=args.project_name,
            docker_executable=args.docker_executable,
            wait_seconds=args.wait_seconds,
            cleanup=args.cleanup,
        )
        if args.evidence_output:
            output = _external_output(args.evidence_output)
            report["evidence"]["evidence_output"] = output.name
            _write_evidence(report, output)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["validation_result"] == "passed" else 1
    except (FileNotFoundError, OSError, ValueError, FileExistsError) as exc:
        print(json.dumps({"validation_result": "blocked", "failure": str(exc), "secret_values_serialized": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
