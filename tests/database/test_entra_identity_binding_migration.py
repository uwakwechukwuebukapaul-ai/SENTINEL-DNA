import sqlite3
import threading

import pytest

from database.backend import SQLiteBackend
from database.migration_runner import MigrationRunner
from database.migrations.registry import NAMESPACE_MIGRATIONS


FOUNDATION, ENTRA, _APPROVAL = NAMESPACE_MIGRATIONS
ISSUER = "https://login.microsoftonline.com/example/v2.0"


def _run_all(backend):
    return MigrationRunner(backend, migrations=()).run()


def _create_user(connection, user_id, username):
    connection.execute(
        "INSERT INTO users(id,username,email,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
        (user_id, username, f"{username}@example.test", "hash", "analyst", "now"),
    )


def _insert_binding(connection, binding_id, user_id=1, *, object_id="object", subject_id="subject", status="active", revoked_at=None):
    connection.execute(
        """INSERT INTO entra_identity_bindings(
           binding_id,user_id,issuer,tenant_id,object_id,subject_id,status,
           created_at,updated_at,created_by,revoked_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (binding_id, user_id, ISSUER, "tenant", object_id, subject_id, status, "now", "now", "reviewer", revoked_at),
    )


def test_fresh_schema_has_required_columns_constraints_and_metadata(tmp_path):
    backend = SQLiteBackend(tmp_path / "fresh.sqlite")
    assert _run_all(backend) == ()
    with backend.session() as connection:
        columns = {row["name"]: row for row in connection.execute("PRAGMA table_info(entra_identity_bindings)")}
        foreign_keys = connection.execute("PRAGMA foreign_key_list(entra_identity_bindings)").fetchall()
        metadata = connection.execute(
            "SELECT namespace,migration_key,status,prerequisites_json FROM migration_records ORDER BY namespace,migration_key"
        ).fetchall()
    assert set(columns) == {
        "binding_id", "user_id", "issuer", "tenant_id", "object_id", "subject_id",
        "status", "created_at", "updated_at", "created_by", "revoked_at",
    }
    assert columns["binding_id"]["pk"] == 1
    assert all(columns[name]["notnull"] for name in columns if name not in {"binding_id", "revoked_at"})
    assert any(row["table"] == "users" and row["from"] == "user_id" and row["to"] == "id" for row in foreign_keys)
    assert [(row["namespace"], row["migration_key"], row["status"]) for row in metadata] == [
        ("foundation", "users_authority", "applied"),
        ("future", "approval_workflow", "applied"),
        ("future", "entra_identity_bindings", "applied"),
    ]
    prerequisites = {row["migration_key"]: row["prerequisites_json"] for row in metadata}
    assert '"migration_key":"users_authority"' in prerequisites["entra_identity_bindings"]
    assert '"migration_key":"entra_identity_bindings"' in prerequisites["approval_workflow"]


def test_prerequisite_is_required_and_legacy_metadata_is_separate(tmp_path):
    backend = SQLiteBackend(tmp_path / "prerequisite.sqlite")
    with pytest.raises(ValueError, match="unknown_migration_prerequisite"):
        MigrationRunner(backend, migrations=(), namespace_migrations=(ENTRA,))
    assert not (tmp_path / "prerequisite.sqlite").exists()


def test_canonical_identity_and_one_active_binding_per_user_are_database_enforced(tmp_path):
    backend = SQLiteBackend(tmp_path / "unique.sqlite")
    _run_all(backend)
    with backend.session() as connection:
        _create_user(connection, 1, "one")
        _create_user(connection, 2, "two")
        _insert_binding(connection, "b1", 1)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_binding(connection, "b2", 2)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_binding(connection, "b3", 1, object_id="other")
        _insert_binding(connection, "b4", 2, object_id="other", subject_id="other-subject")


def test_similar_display_email_upn_and_actor_values_do_not_define_identity(tmp_path):
    backend = SQLiteBackend(tmp_path / "tuple.sqlite")
    _run_all(backend)
    with backend.session() as connection:
        _create_user(connection, 1, "same-name")
        _create_user(connection, 2, "same-name-2")
        _insert_binding(connection, "b1", 1, object_id="oid-a", subject_id="sub-a")
        _insert_binding(connection, "b2", 2, object_id="oid-b", subject_id="sub-b")
        assert connection.execute("SELECT COUNT(*) FROM entra_identity_bindings").fetchone()[0] == 2


def test_revocation_requires_timestamp_blocks_reactivation_and_allows_explicit_new_binding(tmp_path):
    backend = SQLiteBackend(tmp_path / "revocation.sqlite")
    _run_all(backend)
    with backend.session() as connection:
        _create_user(connection, 1, "one")
        _insert_binding(connection, "old")
        connection.execute("UPDATE entra_identity_bindings SET status='revoked', revoked_at='later' WHERE binding_id='old'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE entra_identity_bindings SET status='active', revoked_at=NULL WHERE binding_id='old'")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_binding(connection, "bad", status="revoked")
        _insert_binding(connection, "new", object_id="object", subject_id="subject")
        active = connection.execute(
            "SELECT binding_id,status FROM entra_identity_bindings WHERE issuer=? AND tenant_id=? AND object_id=? AND subject_id=? AND status='active'",
            (ISSUER, "tenant", "object", "subject"),
        ).fetchall()
    assert [tuple(row) for row in active] == [("new", "active")]


def test_nonexistent_user_is_rejected_by_foreign_key_and_revoked_is_not_active(tmp_path):
    backend = SQLiteBackend(tmp_path / "fk.sqlite")
    _run_all(backend)
    with backend.session() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            _insert_binding(connection, "missing", user_id=999)
        _create_user(connection, 1, "one")
        _insert_binding(connection, "revoked", status="revoked", revoked_at="now")
        assert connection.execute("SELECT COUNT(*) FROM entra_identity_bindings WHERE status='active'").fetchone()[0] == 0


def test_compatible_existing_table_is_adopted_without_data_loss_and_extra_columns(tmp_path):
    backend = SQLiteBackend(tmp_path / "adopt.sqlite")
    MigrationRunner(backend, migrations=(), namespace_migrations=(FOUNDATION,)).run()
    with backend.session() as connection:
        connection.execute(
            """CREATE TABLE entra_identity_bindings (
                binding_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                issuer TEXT NOT NULL, tenant_id TEXT NOT NULL,
                object_id TEXT NOT NULL, subject_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                created_by TEXT NOT NULL, revoked_at TEXT,
                legacy_note TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                CHECK((status='active' AND revoked_at IS NULL) OR (status='revoked' AND revoked_at IS NOT NULL))
        )"""
        )
        _create_user(connection, 1, "one")
        _insert_binding(connection, "existing")
        connection.execute("CREATE UNIQUE INDEX uq_entra_binding_active_identity ON entra_identity_bindings(issuer,tenant_id,object_id,subject_id) WHERE status='active'")
        connection.execute("CREATE UNIQUE INDEX uq_entra_binding_active_user ON entra_identity_bindings(user_id) WHERE status='active'")
    _run_all(backend)
    with backend.session() as connection:
        assert connection.execute("SELECT binding_id,user_id FROM entra_identity_bindings").fetchone()[0] == "existing"
        assert "legacy_note" in {row["name"] for row in connection.execute("PRAGMA table_info(entra_identity_bindings)")}


def test_missing_active_uniqueness_fails_closed(tmp_path):
    backend = SQLiteBackend(tmp_path / "missing-uniqueness.sqlite")
    MigrationRunner(backend, migrations=(), namespace_migrations=(FOUNDATION,)).run()
    with backend.session() as connection:
        connection.execute(
            """CREATE TABLE entra_identity_bindings (
                binding_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                issuer TEXT NOT NULL, tenant_id TEXT NOT NULL,
                object_id TEXT NOT NULL, subject_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                created_by TEXT NOT NULL, revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                CHECK((status='active' AND revoked_at IS NULL) OR (status='revoked' AND revoked_at IS NOT NULL))
            )"""
        )
    with pytest.raises(ValueError, match="uniqueness_required"):
        _run_all(backend)


@pytest.mark.parametrize("definition", [
    "binding_id INTEGER PRIMARY KEY",
    "binding_id TEXT, user_id INTEGER NOT NULL",
    "binding_id TEXT PRIMARY KEY, user_id TEXT NOT NULL",
    "binding_id TEXT PRIMARY KEY, user_id INTEGER",
])
def test_incompatible_existing_schema_fails_closed(tmp_path, definition):
    backend = SQLiteBackend(tmp_path / "bad.sqlite")
    MigrationRunner(backend, migrations=(), namespace_migrations=(FOUNDATION,)).run()
    with backend.session() as connection:
        connection.execute(f"CREATE TABLE entra_identity_bindings ({definition})")
    with pytest.raises(ValueError):
        _run_all(backend)


def test_failed_index_creation_rolls_back_metadata_and_schema_changes(tmp_path):
    backend = SQLiteBackend(tmp_path / "rollback.sqlite")
    MigrationRunner(backend, migrations=(), namespace_migrations=(FOUNDATION,)).run()
    with backend.session() as connection:
        connection.execute(
            """CREATE TABLE entra_identity_bindings (
                binding_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                issuer TEXT NOT NULL, tenant_id TEXT NOT NULL,
                object_id TEXT NOT NULL, subject_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                created_by TEXT NOT NULL, revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                CHECK((status='active' AND revoked_at IS NULL) OR (status='revoked' AND revoked_at IS NOT NULL))
            )"""
        )
        _create_user(connection, 1, "one")
        _create_user(connection, 2, "two")
        _insert_binding(connection, "one", 1)
        _insert_binding(connection, "two", 2, object_id="other")
        connection.execute("UPDATE entra_identity_bindings SET object_id='object' WHERE binding_id='two'")
    with pytest.raises(ValueError, match="uniqueness_required"):
        _run_all(backend)
    with backend.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM migration_records WHERE namespace='future'").fetchone()[0] == 0
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uq_entra_binding_active_identity'").fetchone() is None


def test_replay_and_concurrent_execution_are_idempotent(tmp_path):
    path = tmp_path / "concurrent.sqlite"
    assert _run_all(SQLiteBackend(path)) == ()
    assert _run_all(SQLiteBackend(path)) == ()
    results = []

    def run():
        results.append(_run_all(SQLiteBackend(path)))

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == [(), ()]
    with SQLiteBackend(path).session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM migration_records WHERE namespace='future'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0


def test_namespace_registration_excludes_numeric_011_and_other_future_migrations():
    assert [(item.namespace, item.migration_key) for item in NAMESPACE_MIGRATIONS] == [
        ("foundation", "users_authority"),
        ("future", "entra_identity_bindings"),
        ("future", "approval_workflow"),
    ]
