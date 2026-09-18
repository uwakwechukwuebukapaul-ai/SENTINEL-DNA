"""Authoritative schema for server-enforced TOTP MFA."""

VERSION = 9
DESCRIPTION = "Server-enforced MFA state and session records"


def upgrade(connection):
    from database.portability import identity_primary_key, table_columns

    backend = getattr(connection, "backend_name", "sqlite")
    identity = identity_primary_key(backend)

    # The auth service historically bootstrapped this legacy table at runtime.
    # Keep the full current user shape here so a fresh authoritative migration
    # owns the MFA columns before the application starts.
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {identity},
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
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

    columns = table_columns(connection, backend, "users")
    additions = {
        "mfa_secret_ciphertext": "ALTER TABLE users ADD COLUMN mfa_secret_ciphertext TEXT",
        "mfa_enrolled_at": "ALTER TABLE users ADD COLUMN mfa_enrolled_at TEXT",
        "mfa_required": "ALTER TABLE users ADD COLUMN mfa_required INTEGER NOT NULL DEFAULT 0",
        "mfa_last_counter": "ALTER TABLE users ADD COLUMN mfa_last_counter INTEGER",
    }
    for column, statement in additions.items():
        if column not in columns:
            connection.execute(statement)

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mfa_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            session_version INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_mfa_sessions_user_active "
        "ON mfa_sessions(user_id, revoked_at, expires_at)"
    )
