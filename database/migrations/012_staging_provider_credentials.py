"""Staging-only provider credential and authority enrollment schema."""

from __future__ import annotations

VERSION = 12
NAMESPACE = "staging"
MIGRATION_KEY = "staging_authority_enrollment"
DESCRIPTION = "Staging provider-only credentials and authority enrollment"


def _require_staging(connection) -> None:
    import os

    if os.environ.get("SENTINEL_DNA_ENV", "").strip().lower() != "staging":
        raise RuntimeError("staging_provider_credentials_requires_staging")
    if os.environ.get("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "").strip().lower() not in {
        "disposable_staging",
        "disposable_rehearsal",
    }:
        raise RuntimeError("staging_provider_credentials_requires_disposable_target")


def _rebuild_sqlite_users(connection) -> None:
    columns = [
        "id", "username", "email", "password_hash", "role", "created_at",
        "last_login", "is_active", "phone_number", "phone_verified_at",
        "tenant_id", "actor_id", "date_of_birth", "email_verified_at",
        "expires_at", "audit_correlation_id", "mfa_secret_ciphertext",
        "mfa_enrolled_at", "revocation_status", "session_version",
        "mfa_required", "mfa_last_counter",
    ]
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("PRAGMA legacy_alter_table=ON")
    connection.execute("ALTER TABLE users RENAME TO users_012_legacy")
    connection.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            password_authentication_enabled INTEGER NOT NULL DEFAULT 1,
            role TEXT NOT NULL DEFAULT 'analyst',
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            phone_number TEXT,
            phone_verified_at TEXT,
            tenant_id TEXT,
            actor_id TEXT,
            date_of_birth TEXT,
            email_verified_at TEXT,
            expires_at TEXT,
            audit_correlation_id TEXT,
            mfa_secret_ciphertext TEXT,
            mfa_enrolled_at TEXT,
            revocation_status TEXT NOT NULL DEFAULT 'active',
            session_version INTEGER NOT NULL DEFAULT 0,
            mfa_required INTEGER NOT NULL DEFAULT 0,
            mfa_last_counter INTEGER
        )
        """
    )
    joined = ",".join(columns)
    connection.execute(
        f"INSERT INTO users({joined}, password_authentication_enabled) "
        f"SELECT {joined}, 1 FROM users_012_legacy"
    )
    connection.execute("DROP TABLE users_012_legacy")
    connection.execute("PRAGMA legacy_alter_table=OFF")
    connection.execute("PRAGMA foreign_keys=ON")


def upgrade(connection) -> None:
    _require_staging(connection)
    backend = getattr(connection, "backend_name", "sqlite")

    if backend == "postgresql":
        connection.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
        connection.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "password_authentication_enabled INTEGER NOT NULL DEFAULT 1"
        )
    else:
        _rebuild_sqlite_users(connection)

    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS staging_authority_enrollments (
            enrollment_id TEXT PRIMARY KEY,
            authority_id TEXT NOT NULL,
            nonce TEXT NOT NULL UNIQUE,
            enrollment_transaction_id TEXT NOT NULL UNIQUE,
            artifact_hash TEXT NOT NULL UNIQUE CHECK(length(artifact_hash) = 64),
            control_tenant_id TEXT NOT NULL,
            requester_subject TEXT NOT NULL,
            requester_key_id TEXT NOT NULL,
            reviewer_subject TEXT NOT NULL,
            reviewer_key_id TEXT NOT NULL,
            requester_fingerprint TEXT NOT NULL CHECK(length(requester_fingerprint) = 64),
            reviewer_fingerprint TEXT NOT NULL CHECK(length(reviewer_fingerprint) = 64),
            environment TEXT NOT NULL CHECK(environment = 'staging'),
            database_target_identity TEXT NOT NULL,
            application_commit TEXT NOT NULL,
            repository_tree TEXT NOT NULL,
            image_digest TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('ENROLLED','REVOKED','EXPIRED')),
            requester_actor_id TEXT NOT NULL,
            reviewer_actor_id TEXT NOT NULL,
            requester_user_id {"BIGINT" if backend == "postgresql" else "INTEGER"} NOT NULL,
            reviewer_user_id {"BIGINT" if backend == "postgresql" else "INTEGER"} NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY(control_tenant_id) REFERENCES canonical_tenants(tenant_id)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_staging_authority_enrollments_scope "
        "ON staging_authority_enrollments(control_tenant_id, status, expires_at)"
    )
