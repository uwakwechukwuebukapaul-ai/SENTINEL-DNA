"""Optional namespace migration for staging first privileged identity bootstrap."""

from __future__ import annotations

from database.migrations.registry import MigrationRef

NAMESPACE = "staging"
MIGRATION_KEY = "first_privileged_identity_bootstrap"
DESCRIPTION = "Staging first privileged identity bootstrap consumption state"
DISPLAY_VERSION = 11
PREREQUISITES = (
    MigrationRef("foundation", "users_authority"),
    MigrationRef("future", "approval_workflow"),
)


def upgrade(connection) -> None:
    from database.portability import append_only_statements, table_columns

    backend_name = getattr(connection, "backend_name", "sqlite")
    user_id_type = "BIGINT" if backend_name == "postgresql" else "INTEGER"
    columns = table_columns(connection, backend_name, "approval_requests")
    if "bootstrap_consumed_at" not in columns:
        connection.execute(
            "ALTER TABLE approval_requests ADD COLUMN bootstrap_consumed_at TEXT"
        )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS staging_first_privileged_identity_bootstrap_consumptions (
            bootstrap_key TEXT PRIMARY KEY CHECK(bootstrap_key = 'staging-first-privileged-identity-v1'),
            tenant_id TEXT NOT NULL,
            approval_id TEXT NOT NULL,
            approval_transaction_id TEXT NOT NULL UNIQUE,
            correlation_id TEXT NOT NULL,
            user_id {user_id_type} NOT NULL,
            created_actor_id TEXT NOT NULL,
            approver_actor_id TEXT NOT NULL,
            approver_user_id {user_id_type} NOT NULL,
            role TEXT NOT NULL CHECK(role = 'soc_manager'),
            outcome TEXT NOT NULL CHECK(outcome = 'success'),
            consumed_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_staging_first_bootstrap_consumptions_tenant "
        "ON staging_first_privileged_identity_bootstrap_consumptions(tenant_id, consumed_at)"
    )
    for statement in append_only_statements(
        backend_name,
        table_name="staging_first_privileged_identity_bootstrap_consumptions",
        trigger_prefix="staging_first_bootstrap_consumptions_append_only",
        error_message="staging_first_bootstrap_consumptions_are_append_only",
    ):
        connection.execute(statement)
    if backend_name == "postgresql":
        connection.execute(
            """CREATE OR REPLACE FUNCTION staging_first_bootstrap_consumed_guard() RETURNS trigger
               LANGUAGE plpgsql AS $$
               BEGIN
                   IF OLD.bootstrap_consumed_at IS NOT NULL
                      AND NEW.bootstrap_consumed_at IS DISTINCT FROM OLD.bootstrap_consumed_at THEN
                       RAISE EXCEPTION 'bootstrap_consumed_state_is_append_only';
                   END IF;
                   RETURN NEW;
               END; $$"""
        )
        connection.execute("DROP TRIGGER IF EXISTS staging_first_bootstrap_consumed_guard ON approval_requests")
        connection.execute(
            """CREATE TRIGGER staging_first_bootstrap_consumed_guard
               BEFORE UPDATE ON approval_requests
               FOR EACH ROW EXECUTE FUNCTION staging_first_bootstrap_consumed_guard()"""
        )
    else:
        connection.execute(
            """CREATE TRIGGER IF NOT EXISTS staging_first_bootstrap_consumed_guard
               BEFORE UPDATE ON approval_requests
               WHEN OLD.bootstrap_consumed_at IS NOT NULL
                AND NEW.bootstrap_consumed_at IS NOT OLD.bootstrap_consumed_at
               BEGIN SELECT RAISE(ABORT, 'bootstrap_consumed_state_is_append_only'); END"""
        )
