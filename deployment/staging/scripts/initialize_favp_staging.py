"""Initialize disposable FAVP staging state.

This command is intentionally staging-only. It applies the core migration
chain plus the staging-only FAVP migration, initializes the dedicated
evidence-volume marker, and records one infrastructure audit event. It never
creates an organization, participant, analyst identity, result, or
validation.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig  # noqa: E402
from database.connection import database_for_environment  # noqa: E402
from database.migration_runner import MigrationRunner  # noqa: E402
from database.migrations.registry import STAGING_MIGRATIONS  # noqa: E402
from database.staging_favp_bootstrap import initialize_staging_artifacts  # noqa: E402


def _audit_guard_count(connection, backend_name: str) -> int:
    def scalar(row):
        return row["count"] if hasattr(row, "keys") else row[0]

    if backend_name == "sqlite":
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM sqlite_master WHERE type='trigger' AND name LIKE 'audit_events_append_only_%'"
        ).fetchone()
        return int(scalar(row))
    row = connection.execute(
        """SELECT COUNT(*) AS count FROM pg_trigger t
           JOIN pg_class c ON c.oid=t.tgrelid
           WHERE c.relname='audit_events' AND NOT t.tgisinternal
             AND t.tgname LIKE 'audit_events_append_only_%'"""
    ).fetchone()
    return int(scalar(row))


def initialize(evidence_dir: str | None = None) -> dict:
    runtime = RuntimeConfig.from_environment()
    runtime.validate()
    if runtime.environment != "staging":
        raise RuntimeError("FAVP staging initialization requires SENTINEL_DNA_ENV=staging")
    if os.getenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") != "1":
        raise RuntimeError("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED must be 1")
    if os.getenv("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") != "1":
        raise RuntimeError("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY must be 1")
    if os.getenv("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") != "0":
        raise RuntimeError("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS must be 0")

    storage = Path(str(evidence_dir or os.getenv("SENTINEL_DNA_FAVP_EVIDENCE_DIR", ""))).expanduser()
    backend = database_for_environment(require_postgresql=True)
    applied = MigrationRunner(backend, migrations=STAGING_MIGRATIONS).run()
    initialize_staging_artifacts(backend, storage)

    with backend.session() as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM audit_events").fetchone()
        audit_events = int(row["count"] if hasattr(row, "keys") else row[0])
        append_only_guards = _audit_guard_count(connection, backend.backend_name)
        row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
        migration_version = int(row["version"] if hasattr(row, "keys") else row[0])

    if migration_version < 9 or audit_events < 1 or append_only_guards < 2:
        raise RuntimeError("FAVP staging initialization verification failed")
    return {
        "status": "FAVP_STAGING_INITIALIZED",
        "migrations_applied": list(applied),
        "migration_version": migration_version,
        "audit_events": audit_events,
        "append_only_guards": append_only_guards,
        "evidence_dir": str(storage),
        "participant_records_created": 0,
        "validation_results_created": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize disposable FAVP staging state")
    parser.add_argument("--evidence-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(initialize(args.evidence_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
