"""Execute the checked-in database migration chain for a deployment."""

from __future__ import annotations

import os

from config.runtime import RuntimeConfig
from database.connection import database_for_environment
from database.migration_runner import MigrationRunner
from database.migrations.registry import apply_staging_first_privileged_identity_namespace


def staging_first_namespace_enabled(environment: str, environ: dict[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    enabled = values.get("SENTINEL_DNA_STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAP_ENABLED") == "1"
    normalized_environment = str(environment).strip().lower()
    if enabled and normalized_environment != "staging":
        raise RuntimeError(
            "staging-first privileged identity bootstrap migration requires staging"
        )
    return enabled


def main() -> int:
    runtime = RuntimeConfig.from_environment()
    runtime.validate()
    bootstrap_namespace_enabled = staging_first_namespace_enabled(runtime.environment)
    backend = database_for_environment(
        require_postgresql=runtime.environment in {"staging", "production"}
    )
    applied = MigrationRunner(backend).run()
    namespace_applied: tuple[int, ...] = ()
    if bootstrap_namespace_enabled:
        namespace_applied = apply_staging_first_privileged_identity_namespace(
            backend,
            environment=runtime.environment,
            enabled=bootstrap_namespace_enabled,
        )
    versions = ",".join(str(version) for version in applied) or "none"
    namespace_versions = ",".join(str(version) for version in namespace_applied) or "none"
    print(f"database migrations applied: {versions}; staging-first namespace: {namespace_versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
