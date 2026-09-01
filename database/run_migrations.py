"""Execute the checked-in database migration chain for a deployment."""

from __future__ import annotations

import os

from config.runtime import RuntimeConfig
from database.connection import database_for_environment
from database.migration_runner import MigrationRunner
from database.migrations.registry import MIGRATIONS, STAGING_MIGRATIONS


def main() -> int:
    runtime = RuntimeConfig.from_environment()
    runtime.validate()
    favp_enabled = runtime.environment == "staging" and os.getenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") == "1"
    if favp_enabled:
        if os.getenv("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") != "1":
            raise RuntimeError("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY must be 1 for FAVP staging initialization")
        if os.getenv("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") != "0":
            raise RuntimeError("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS must be 0 for FAVP staging initialization")
    backend = database_for_environment(
        require_postgresql=runtime.environment in {"staging", "production"}
    )
    migrations = STAGING_MIGRATIONS if favp_enabled else MIGRATIONS
    applied = MigrationRunner(backend, migrations=migrations).run()
    if favp_enabled:
        from database.staging_favp_bootstrap import initialize_staging_artifacts
        initialize_staging_artifacts(backend, os.getenv("SENTINEL_DNA_FAVP_EVIDENCE_DIR"))
    versions = ",".join(str(version) for version in applied) or "none"
    print(f"database migrations applied: {versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
