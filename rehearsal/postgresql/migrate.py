"""Run and verify the PostgreSQL migration/idempotency rehearsal."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database.backend import PostgreSQLBackend  # noqa: E402
from database.migration_runner import MigrationRunner  # noqa: E402
from database.migrations.registry import MIGRATIONS  # noqa: E402

try:  # noqa: E402 - supports both module and direct-script execution
    from .common import digest
except ImportError:  # pragma: no cover - direct operator invocation
    from common import digest


# This is the exact table inventory owned by the authoritative default
# migration registry (001-008). It intentionally excludes staging overlay 011
# and the legacy normalized-core schema contract in database.schema.
AUTHORITATIVE_MIGRATION_TABLES = (
    "analyst_actions",
    "audit_events",
    "billing_customers",
    "billing_events",
    "billing_subscriptions",
    "billing_transactions",
    "canonical_identities",
    "canonical_identity_bindings",
    "canonical_memberships",
    "canonical_provider_tenant_trusts",
    "canonical_schema_metadata",
    "canonical_tenants",
    "case_notes",
    "cases",
    "crypto_payment_intents",
    "crypto_quotes",
    "evidence",
    "incidents",
    "investigation_memory",
    "investigation_memory_audit",
    "investigation_memory_feedback",
    "iocs",
    "organizational_memory",
    "organizational_memory_audit",
    "schema_migrations",
    "timeline",
)


def authoritative_migration_table_names() -> tuple[str, ...]:
    """Return the fail-closed inventory for the default migration chain."""

    return AUTHORITATIVE_MIGRATION_TABLES


def _table_names(backend: PostgreSQLBackend) -> list[str]:
    with backend.session() as connection:
        rows = connection.execute(
            """SELECT table_name FROM information_schema.tables
               WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'
               ORDER BY table_name"""
        ).fetchall()
    return [str(row["table_name"]) for row in rows]


def assert_empty_target(backend: PostgreSQLBackend) -> None:
    with backend.session() as connection:
        row = connection.execute(
            """SELECT COUNT(*) AS count FROM information_schema.tables
               WHERE table_schema = current_schema()"""
        ).fetchone()
    if int(row["count"]) != 0:
        raise RuntimeError("rehearsal_target_must_be_empty")


def run_migration(backend: PostgreSQLBackend, *, require_empty: bool = True) -> dict[str, Any]:
    if require_empty:
        assert_empty_target(backend)
    runner = MigrationRunner(backend)
    first = runner.run()
    second = runner.run()
    tables = _table_names(backend)
    expected = sorted(authoritative_migration_table_names())
    if tables != expected:
        raise RuntimeError("representative_schema_inventory_mismatch")
    return {
        "migration_versions_first_run": list(first),
        "migration_versions_second_run": list(second),
        "schema_tables": tables,
        "schema_digest": digest(tables),
        "migration_ordering": first == tuple(migration.version for migration in MIGRATIONS),
        "migration_idempotency": second == (),
        "schema_compatibility": tables == expected,
    }
