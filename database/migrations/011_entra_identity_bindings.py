"""Additive Entra identity bindings.

This migration does not alter users, canonical identities, historical records,
or the generic identity-link tables.  Bindings are intentionally inert until
the Entra OIDC route is explicitly configured.
"""

VERSION = 11
DESCRIPTION = "Entra OIDC identity bindings"


def upgrade(connection) -> None:
    # AuthService currently owns users-table creation.  Keep this migration
    # inert/unregistered until deployment proves that users exists first.
    try:
        connection.execute("SELECT 1 FROM users LIMIT 0")
    except Exception as exc:
        raise RuntimeError("users_table_required_before_entra_identity_bindings")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS entra_identity_bindings (
            binding_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            issuer TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'disabled', 'revoked')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            revoked_at TEXT,
            UNIQUE(issuer, tenant_id, object_id, subject_id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )"""
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_entra_active_tuple "
        "ON entra_identity_bindings(issuer, tenant_id, object_id, subject_id) "
        "WHERE status = 'active'"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_entra_bindings_user "
        "ON entra_identity_bindings(user_id, status)"
    )


def downgrade(connection) -> None:
    connection.execute("DROP INDEX IF EXISTS idx_entra_bindings_user")
    connection.execute("DROP INDEX IF EXISTS uq_entra_active_tuple")
    connection.execute("DROP TABLE IF EXISTS entra_identity_bindings")
