"""Exercise transactional rollback against the disposable PostgreSQL target."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database.backend import PostgreSQLBackend  # noqa: E402
from database.migration_runner import CORE_MIGRATIONS, Migration, MigrationRunner  # noqa: E402


def run_rollback(backend: PostgreSQLBackend) -> dict[str, Any]:
    connection = backend.connect()
    try:
        connection.execute("CREATE TABLE rollback_transaction_probe (value TEXT NOT NULL)")
        connection.rollback()
        row = connection.execute(
            "SELECT to_regclass('public.rollback_transaction_probe') AS table_name"
        ).fetchone()
        transaction_rollback = row["table_name"] is None
    finally:
        connection.close()

    failing = Migration(
        version=2,
        name="intentional_failure_for_rehearsal",
        statements=lambda _backend: (
            "CREATE TABLE rollback_migration_probe (value TEXT NOT NULL)",
            "THIS IS INVALID SQL",
        ),
    )
    try:
        MigrationRunner(backend, migrations=CORE_MIGRATIONS + (failing,)).run()
    except Exception:
        migration_failure_observed = True
    else:
        migration_failure_observed = False

    with backend.session() as check:
        version_rows = check.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        probe = check.execute(
            "SELECT to_regclass('public.rollback_migration_probe') AS table_name"
        ).fetchone()
    versions = [int(row["version"]) for row in version_rows]
    migration_rollback = migration_failure_observed and versions == [1] and probe["table_name"] is None
    return {
        "transaction_rollback": transaction_rollback,
        "migration_failure_observed": migration_failure_observed,
        "migration_rollback": migration_rollback,
        "backup_restore_rehearsal": "not_executed",
    }
