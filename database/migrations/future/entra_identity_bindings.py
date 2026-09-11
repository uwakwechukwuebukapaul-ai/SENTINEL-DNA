"""Persistent bindings from verified Entra identities to local users.

The stored state values are lowercase ``active`` and ``revoked`` to remain
compatible with the existing read-only OIDC resolver.  They are the storage
representation of the documented ACTIVE and REVOKED states.
"""

from __future__ import annotations

import re
from typing import Any


NAMESPACE = "future"
MIGRATION_KEY = "entra_identity_bindings"
DESCRIPTION = "Entra identity bindings"
from database.migrations.registry import MigrationRef

PREREQUISITES = (MigrationRef("foundation", "users_authority"),)

_COLUMNS = {
    "binding_id": ("text", False),
    "user_id": ("integer", True),
    "issuer": ("text", True),
    "tenant_id": ("text", True),
    "object_id": ("text", True),
    "subject_id": ("text", True),
    "status": ("text", True),
    "created_at": ("text", True),
    "updated_at": ("text", True),
    "created_by": ("text", True),
    "revoked_at": ("text", False),
}
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _backend_name(connection: Any) -> str:
    return getattr(connection, "backend_name", "sqlite")


def _quote_identifier(identifier: str) -> str:
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError("invalid_schema_identifier")
    return identifier


def _table_exists(connection: Any, backend_name: str) -> bool:
    if backend_name == "sqlite":
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entra_identity_bindings'"
        ).fetchone() is not None
    return connection.execute(
        """SELECT EXISTS (
               SELECT 1 FROM information_schema.tables
               WHERE table_schema=current_schema() AND table_name='entra_identity_bindings'
           ) AS present"""
    ).fetchone()["present"]


def _create_table(connection: Any, backend_name: str) -> None:
    user_id = "BIGINT" if backend_name == "postgresql" else "INTEGER"
    connection.execute(
        f"""CREATE TABLE entra_identity_bindings (
            binding_id TEXT PRIMARY KEY,
            user_id {user_id} NOT NULL,
            issuer TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'revoked')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            CHECK(
                (status = 'active' AND revoked_at IS NULL)
                OR (status = 'revoked' AND revoked_at IS NOT NULL)
            )
        )"""
    )
    _create_indexes(connection, backend_name)
    _create_guards(connection, backend_name)


def _create_indexes(connection: Any, backend_name: str) -> None:
    if backend_name == "postgresql":
        connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_entra_binding_active_identity
               ON entra_identity_bindings(issuer, tenant_id, object_id, subject_id)
               WHERE status = 'active'"""
        )
        connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_entra_binding_active_user
               ON entra_identity_bindings(user_id)
               WHERE status = 'active'"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_entra_binding_user_status
               ON entra_identity_bindings(user_id, status)"""
        )
        return
    connection.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_entra_binding_active_identity
           ON entra_identity_bindings(issuer, tenant_id, object_id, subject_id)
           WHERE status = 'active'"""
    )
    connection.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS uq_entra_binding_active_user
           ON entra_identity_bindings(user_id)
           WHERE status = 'active'"""
    )
    connection.execute(
        """CREATE INDEX IF NOT EXISTS idx_entra_binding_user_status
           ON entra_identity_bindings(user_id, status)"""
    )


def _create_guards(connection: Any, backend_name: str) -> None:
    if backend_name == "postgresql":
        connection.execute(
            """CREATE OR REPLACE FUNCTION entra_binding_state_guard() RETURNS trigger
               LANGUAGE plpgsql AS $$
               BEGIN
                   IF OLD.status = 'revoked' AND NEW.status = 'active' THEN
                       RAISE EXCEPTION 'revoked_binding_cannot_reactivate';
                   END IF;
                   IF NEW.status = 'active' AND NEW.revoked_at IS NOT NULL THEN
                       RAISE EXCEPTION 'active_binding_cannot_have_revoked_at';
                   END IF;
                   IF NEW.status = 'revoked' AND NEW.revoked_at IS NULL THEN
                       RAISE EXCEPTION 'revoked_binding_requires_revoked_at';
                   END IF;
                   RETURN NEW;
               END; $$"""
        )
        connection.execute("DROP TRIGGER IF EXISTS entra_binding_state_guard ON entra_identity_bindings")
        connection.execute(
            """CREATE TRIGGER entra_binding_state_guard
               BEFORE INSERT OR UPDATE ON entra_identity_bindings
               FOR EACH ROW EXECUTE FUNCTION entra_binding_state_guard()"""
        )
        return
    connection.execute(
        """CREATE TRIGGER IF NOT EXISTS entra_binding_no_reactivation
           BEFORE UPDATE OF status ON entra_identity_bindings
           WHEN OLD.status = 'revoked' AND NEW.status = 'active'
           BEGIN SELECT RAISE(ABORT, 'revoked_binding_cannot_reactivate'); END"""
    )
    connection.execute(
        """CREATE TRIGGER IF NOT EXISTS entra_binding_state_guard
           BEFORE INSERT ON entra_identity_bindings
           WHEN (NEW.status = 'active' AND NEW.revoked_at IS NOT NULL)
             OR (NEW.status = 'revoked' AND NEW.revoked_at IS NULL)
           BEGIN SELECT RAISE(ABORT, 'binding_state_timestamp_mismatch'); END"""
    )
    connection.execute(
        """CREATE TRIGGER IF NOT EXISTS entra_binding_update_state_guard
           BEFORE UPDATE OF status, revoked_at ON entra_identity_bindings
           WHEN (NEW.status = 'active' AND NEW.revoked_at IS NOT NULL)
             OR (NEW.status = 'revoked' AND NEW.revoked_at IS NULL)
           BEGIN SELECT RAISE(ABORT, 'binding_state_timestamp_mismatch'); END"""
    )


def _columns(connection: Any, backend_name: str) -> dict[str, dict[str, Any]]:
    if backend_name == "sqlite":
        return {
            row["name"]: {
                "type": str(row["type"] or "").lower(),
                "notnull": bool(row["notnull"]),
                "pk": int(row["pk"]),
            }
            for row in connection.execute("PRAGMA table_info(entra_identity_bindings)").fetchall()
        }
    rows = connection.execute(
        """SELECT column_name, data_type, is_nullable
           FROM information_schema.columns
           WHERE table_schema=current_schema() AND table_name='entra_identity_bindings'"""
    ).fetchall()
    return {
        row["column_name"]: {
            "type": str(row["data_type"]).lower(),
            "notnull": row["is_nullable"] == "NO",
            "pk": 0,
        }
        for row in rows
    }


def _validate_foreign_key(connection: Any, backend_name: str) -> None:
    if backend_name == "sqlite":
        foreign_keys = connection.execute("PRAGMA foreign_key_list(entra_identity_bindings)").fetchall()
        if not any(
            row["table"] == "users" and row["from"] == "user_id" and row["to"] == "id"
            for row in foreign_keys
        ):
            raise ValueError("entra_binding_users_fk_required")
        return
    row = connection.execute(
        """SELECT EXISTS (
             SELECT 1
             FROM information_schema.table_constraints tc
             JOIN information_schema.key_column_usage kcu
               ON kcu.constraint_name=tc.constraint_name
              AND kcu.table_schema=tc.table_schema
             JOIN information_schema.constraint_column_usage ccu
               ON ccu.constraint_name=tc.constraint_name
              AND ccu.constraint_schema=tc.constraint_schema
             WHERE tc.table_schema=current_schema()
               AND tc.table_name='entra_identity_bindings'
               AND tc.constraint_type='FOREIGN KEY'
               AND kcu.column_name='user_id'
               AND ccu.table_name='users'
               AND ccu.column_name='id'
           ) AS present"""
    ).fetchone()
    if not row["present"]:
        raise ValueError("entra_binding_users_fk_required")


def _validate_active_unique_indexes(connection: Any, backend_name: str) -> None:
    if backend_name == "sqlite":
        identity_index = False
        user_index = False
        for row in connection.execute("PRAGMA index_list(entra_identity_bindings)").fetchall():
            if not bool(row["unique"]):
                continue
            index_name = str(row["name"])
            columns = [
                item["name"]
                for item in connection.execute(
                    f"PRAGMA index_info({_quote_identifier(index_name)})"
                ).fetchall()
            ]
            definition = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                (index_name,),
            ).fetchone()
            normalized = re.sub(r"\s+", "", str(definition[0] if definition else "").lower())
            active = "where status='active'" in normalized or index_name in {
                "uq_entra_binding_active_identity", "uq_entra_binding_active_user"
            }
            identity_index = identity_index or (active and columns == ["issuer", "tenant_id", "object_id", "subject_id"])
            user_index = user_index or (active and columns == ["user_id"])
        if not identity_index:
            raise ValueError("entra_binding_identity_uniqueness_required")
        if not user_index:
            raise ValueError("entra_binding_active_user_uniqueness_required")
        return
    rows = connection.execute(
        """SELECT indexdef FROM pg_indexes
           WHERE schemaname=current_schema() AND tablename='entra_identity_bindings'"""
    ).fetchall()
    definitions = [re.sub(r"\s+", "", str(row["indexdef"]).lower()) for row in rows]
    if not any(
        "uniqueindex" in definition
        and "(issuer,tenant_id,object_id,subject_id)" in definition
        and "wherestatus='active'" in definition
        for definition in definitions
    ):
        raise ValueError("entra_binding_identity_uniqueness_required")
    if not any(
        "uniqueindex" in definition
        and "(user_id)" in definition
        and "wherestatus='active'" in definition
        for definition in definitions
    ):
        raise ValueError("entra_binding_active_user_uniqueness_required")


def _validate_primary_key(connection: Any, backend_name: str, columns: dict[str, dict[str, Any]]) -> None:
    if backend_name == "sqlite":
        if columns["binding_id"]["pk"] != 1 or sum(item["pk"] > 0 for item in columns.values()) != 1:
            raise ValueError("entra_binding_incompatible_primary_key")
        return
    row = connection.execute(
        """SELECT COUNT(*) AS count
           FROM information_schema.table_constraints tc
           JOIN information_schema.key_column_usage kcu
             ON kcu.constraint_name=tc.constraint_name
            AND kcu.table_schema=tc.table_schema
           WHERE tc.table_schema=current_schema()
             AND tc.table_name='entra_identity_bindings'
             AND tc.constraint_type='PRIMARY KEY'
             AND kcu.column_name='binding_id'"""
    ).fetchone()
    if int(row["count"]) != 1:
        raise ValueError("entra_binding_incompatible_primary_key")


def _validate_existing(connection: Any, backend_name: str) -> None:
    columns = _columns(connection, backend_name)
    missing = set(_COLUMNS) - set(columns)
    if missing:
        raise ValueError(f"entra_binding_missing_columns:{','.join(sorted(missing))}")
    for name, (expected_type, expected_notnull) in _COLUMNS.items():
        column = columns[name]
        if column["type"] != expected_type:
            raise ValueError(f"entra_binding_incompatible_column_type:{name}")
        if expected_notnull and not column["notnull"]:
            raise ValueError(f"entra_binding_unsafe_nullability:{name}")
    _validate_primary_key(connection, backend_name, columns)
    if backend_name == "sqlite":
        table_sql = str(connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='entra_identity_bindings'"
        ).fetchone()[0]).lower()
        if "check(statusin('active','revoked'))" not in re.sub(r"\s+", "", table_sql):
            raise ValueError("entra_binding_status_constraint_required")
    _validate_foreign_key(connection, backend_name)
    _validate_active_unique_indexes(connection, backend_name)


def validate_binding_schema(connection: Any, backend_name: str | None = None) -> None:
    """Read-only validation for identity-binding consumers."""

    backend = backend_name or _backend_name(connection)
    if not _table_exists(connection, backend):
        raise ValueError("entra_identity_bindings_table_missing")
    _validate_existing(connection, backend)


def upgrade(connection: Any) -> None:
    backend_name = _backend_name(connection)
    if not _table_exists(connection, backend_name):
        _create_table(connection, backend_name)
        return
    _validate_existing(connection, backend_name)
    _create_indexes(connection, backend_name)
    _create_guards(connection, backend_name)
