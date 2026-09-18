"""Explicit staging-only schema for first privileged identity authorization."""

from __future__ import annotations

VERSION = 11
NAMESPACE = "staging"
MIGRATION_KEY = "first_privileged_identity_bootstrap"
DESCRIPTION = "Staging first privileged identity authorization and consumption state"
DISPLAY_VERSION = 11
PREREQUISITES = ()


def upgrade(connection) -> None:
    from database.portability import append_only_statements

    backend_name = getattr(connection, "backend_name", "sqlite")
    user_id_type = "BIGINT" if backend_name == "postgresql" else "INTEGER"
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS staging_bootstrap_authorizations (
            authorization_id TEXT PRIMARY KEY,
            control_tenant_id TEXT NOT NULL,
            requester_actor_id TEXT NOT NULL,
            requester_user_id {user_id_type} NOT NULL,
            requester_provider TEXT NOT NULL,
            requester_subject TEXT NOT NULL,
            requester_credential_id TEXT NOT NULL,
            requester_verified_at TEXT NOT NULL,
            operation TEXT NOT NULL CHECK(operation = 'staging_first_privileged_identity_bootstrap'),
            purpose TEXT NOT NULL CHECK(purpose = 'create_first_staging_control_tenant_soc_manager'),
            environment TEXT NOT NULL CHECK(environment = 'staging'),
            target_username TEXT NOT NULL,
            target_email TEXT NOT NULL,
            target_role TEXT NOT NULL CHECK(target_role = 'soc_manager'),
            database_target_identity TEXT NOT NULL,
            approval_transaction_id TEXT NOT NULL UNIQUE,
            artifact_hash TEXT NOT NULL CHECK(length(artifact_hash) = 64),
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('REQUESTED','APPROVED','REJECTED','EXPIRED','CONSUMED')),
            reviewer_actor_id TEXT,
            reviewer_user_id {user_id_type},
            reviewer_provider TEXT,
            reviewer_subject TEXT,
            reviewer_credential_id TEXT,
            reviewer_verified_at TEXT,
            decided_at TEXT,
            consumed_at TEXT,
            bootstrap_correlation_id TEXT UNIQUE,
            created_user_id {user_id_type},
            created_actor_id TEXT,
            created_at TEXT NOT NULL,
            CHECK(reviewer_actor_id IS NULL OR reviewer_actor_id <> requester_actor_id),
            FOREIGN KEY(control_tenant_id) REFERENCES canonical_tenants(tenant_id)
        )"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_staging_bootstrap_authorizations_scope ON staging_bootstrap_authorizations(control_tenant_id, status, expires_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_staging_bootstrap_authorizations_requester ON staging_bootstrap_authorizations(requester_actor_id)")
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS staging_bootstrap_consumptions (
            bootstrap_key TEXT PRIMARY KEY CHECK(bootstrap_key = 'staging-first-privileged-identity-v1'),
            authorization_id TEXT NOT NULL UNIQUE,
            approval_transaction_id TEXT NOT NULL UNIQUE,
            bootstrap_correlation_id TEXT NOT NULL UNIQUE,
            control_tenant_id TEXT NOT NULL,
            requester_actor_id TEXT NOT NULL,
            reviewer_actor_id TEXT NOT NULL,
            reviewer_user_id {user_id_type} NOT NULL,
            created_user_id {user_id_type} NOT NULL,
            created_actor_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role = 'soc_manager'),
            outcome TEXT NOT NULL CHECK(outcome = 'success'),
            consumed_at TEXT NOT NULL,
            FOREIGN KEY(authorization_id) REFERENCES staging_bootstrap_authorizations(authorization_id),
            FOREIGN KEY(control_tenant_id) REFERENCES canonical_tenants(tenant_id)
        )"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_staging_bootstrap_consumptions_tenant ON staging_bootstrap_consumptions(control_tenant_id, consumed_at)")
    for statement in append_only_statements(backend_name, table_name="staging_bootstrap_consumptions", trigger_prefix="staging_bootstrap_consumptions_append_only", error_message="staging_bootstrap_consumptions_are_append_only"):
        connection.execute(statement)

    immutable_columns = (
        "authorization_id", "control_tenant_id", "requester_actor_id", "requester_user_id",
        "requester_provider", "requester_subject", "requester_credential_id", "requester_verified_at",
        "operation", "purpose", "environment", "target_username", "target_email", "target_role",
        "database_target_identity", "approval_transaction_id", "artifact_hash", "expires_at",
    )
    if backend_name == "postgresql":
        comparisons = " OR ".join(f"OLD.{column} IS DISTINCT FROM NEW.{column}" for column in immutable_columns)
        connection.execute(
            f"""CREATE OR REPLACE FUNCTION staging_bootstrap_authorization_immutable_guard() RETURNS trigger
               LANGUAGE plpgsql AS $$
               BEGIN
                   IF {comparisons} THEN
                       RAISE EXCEPTION 'staging_bootstrap_artifact_is_immutable';
                   END IF;
                   RETURN NEW;
               END; $$"""
        )
        connection.execute("DROP TRIGGER IF EXISTS staging_bootstrap_authorization_immutable_guard ON staging_bootstrap_authorizations")
        connection.execute("CREATE TRIGGER staging_bootstrap_authorization_immutable_guard BEFORE UPDATE ON staging_bootstrap_authorizations FOR EACH ROW EXECUTE FUNCTION staging_bootstrap_authorization_immutable_guard()")
    else:
        comparisons = " OR ".join(f"OLD.{column} IS NOT NEW.{column}" for column in immutable_columns)
        connection.execute(
            f"""CREATE TRIGGER IF NOT EXISTS staging_bootstrap_authorization_immutable_guard
               BEFORE UPDATE ON staging_bootstrap_authorizations
               WHEN {comparisons}
               BEGIN SELECT RAISE(ABORT, 'staging_bootstrap_artifact_is_immutable'); END"""
        )
