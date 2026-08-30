"""Execute the checked-in database migration chain for a deployment."""

from __future__ import annotations

from config.runtime import RuntimeConfig
from database.connection import database_for_environment
from database.migration_runner import MigrationRunner


def main() -> int:
    runtime = RuntimeConfig.from_environment()
    runtime.validate()
    backend = database_for_environment(
        require_postgresql=runtime.environment in {"staging", "production"}
    )
    applied = MigrationRunner(backend).run()
    versions = ",".join(str(version) for version in applied) or "none"
    print(f"database migrations applied: {versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
