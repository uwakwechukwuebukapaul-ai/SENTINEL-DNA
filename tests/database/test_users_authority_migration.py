import hashlib
import sqlite3
import threading

import pytest

from database.backend import SQLiteBackend
from database.migration_runner import CONTROLLED_ANALYST_PILOT_MIGRATIONS, MigrationRunner
from database.migrations.registry import NAMESPACE_MIGRATIONS


BASE_COLUMNS = {
    "id", "username", "email", "password_hash", "role", "created_at",
    "last_login", "is_active",
}
RUNTIME_COLUMNS = {
    "phone_number", "phone_verified_at", "tenant_id", "actor_id", "date_of_birth",
    "email_verified_at", "expires_at", "audit_correlation_id", "revocation_status",
    "session_version", "onboarding_state",
}


def _runner(backend):
    return MigrationRunner(backend, migrations=(), namespace_migrations=(NAMESPACE_MIGRATIONS[0],))


def _create_legacy_users(path, *, extra="", unique_username=True, unique_email=True, id_type="INTEGER"):
    username = "username TEXT NOT NULL" + (" UNIQUE" if unique_username else "")
    email = "email TEXT NOT NULL" + (" UNIQUE" if unique_email else "")
    connection = sqlite3.connect(path)
    connection.execute(
        f"""CREATE TABLE users (
            id {id_type} PRIMARY KEY AUTOINCREMENT,
            {username}, {email}, password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'analyst', created_at TEXT NOT NULL,
            last_login TEXT, is_active INTEGER NOT NULL DEFAULT 1{extra}
        )"""
    )
    connection.execute(
        "INSERT INTO users(id,username,email,password_hash,role,created_at,last_login) VALUES (?,?,?,?,?,?,?)",
        (41, "legacy-user", "legacy@example.test", "hash", "analyst", "2026-01-01T00:00:00Z", None),
    )
    connection.commit()
    connection.close()


def _columns(backend):
    with backend.session() as connection:
        return {
            row["name"]: row
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }


def test_fresh_sqlite_creates_authoritative_users_schema_and_metadata(tmp_path):
    backend = SQLiteBackend(tmp_path / "fresh.sqlite")

    assert _runner(backend).run() == ()
    columns = _columns(backend)
    assert BASE_COLUMNS | RUNTIME_COLUMNS <= set(columns)
    assert columns["id"]["type"] == "INTEGER" and columns["id"]["pk"] == 1
    with backend.session() as connection:
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()[0]
        record = connection.execute(
            "SELECT namespace,migration_key,status FROM migration_records"
        ).fetchone()
    assert "AUTOINCREMENT" in table_sql.upper()
    assert tuple(record) == ("foundation", "users_authority", "applied")


def test_original_eight_column_schema_is_adopted_without_data_or_id_loss(tmp_path):
    path = tmp_path / "original.sqlite"
    _create_legacy_users(path)
    backend = SQLiteBackend(path)

    assert _runner(backend).run() == ()
    with backend.session() as connection:
        row = connection.execute(
            "SELECT id,username,email,password_hash,role,created_at,last_login FROM users"
        ).fetchone()
        connection.execute("INSERT INTO users(username,email,password_hash,created_at) VALUES (?,?,?,?)", ("second", "second@example.test", "h", "now"))
        second_id = connection.execute("SELECT id FROM users WHERE username='second'").fetchone()[0]
    assert tuple(row) == (41, "legacy-user", "legacy@example.test", "hash", "analyst", "2026-01-01T00:00:00Z", None)
    assert second_id > 41
    assert BASE_COLUMNS | RUNTIME_COLUMNS <= set(_columns(backend))


def test_partially_upgraded_schema_and_extra_columns_are_preserved(tmp_path):
    path = tmp_path / "partial.sqlite"
    _create_legacy_users(path, extra=", phone_number TEXT, session_version INTEGER NOT NULL DEFAULT 0, legacy_flag TEXT")
    backend = SQLiteBackend(path)

    _runner(backend).run()
    columns = _columns(backend)
    assert BASE_COLUMNS | RUNTIME_COLUMNS | {"legacy_flag"} <= set(columns)


@pytest.mark.parametrize("case", ["primary_key", "username_unique", "email_unique", "required_type", "required_nullable"])
def test_incompatible_existing_schema_fails_closed(tmp_path, case):
    path = tmp_path / f"incompatible-{case}.sqlite"
    if case == "primary_key":
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL, last_login TEXT, is_active INTEGER NOT NULL)")
        connection.commit(); connection.close()
    elif case == "username_unique":
        _create_legacy_users(path, unique_username=False)
    elif case == "email_unique":
        _create_legacy_users(path, unique_email=False)
    elif case == "required_type":
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash INTEGER NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL, last_login TEXT, is_active INTEGER NOT NULL)")
        connection.commit(); connection.close()
    else:
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT, created_at TEXT NOT NULL, last_login TEXT, is_active INTEGER NOT NULL)")
        connection.commit(); connection.close()

    with pytest.raises(ValueError):
        _runner(SQLiteBackend(path)).run()
    connection = sqlite3.connect(path)
    assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] in (0, 1)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='migration_records'").fetchone() is None
    connection.close()


def test_foreign_key_can_reference_users_id_without_creating_identity_tables(tmp_path):
    backend = SQLiteBackend(tmp_path / "fk.sqlite")
    _runner(backend).run()
    with backend.session() as connection:
        connection.execute("CREATE TABLE auth_identities (user_id INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
        connection.execute("INSERT INTO users(username,email,password_hash,created_at) VALUES (?,?,?,?)", ("u", "u@example.test", "h", "now"))
        connection.execute("INSERT INTO auth_identities(user_id) VALUES (1)")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO auth_identities(user_id) VALUES (999)")


def test_replay_is_idempotent_and_namespace_metadata_does_not_touch_legacy_versions(tmp_path):
    backend = SQLiteBackend(tmp_path / "replay.sqlite")
    assert _runner(backend).run() == ()
    assert _runner(backend).run() == ()
    with backend.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM migration_records").fetchone()[0] == 1


def test_concurrent_runners_apply_users_authority_once(tmp_path):
    path = tmp_path / "concurrent.sqlite"
    results = []

    def run():
        results.append(_runner(SQLiteBackend(path)).run())

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == [(), ()]
    with SQLiteBackend(path).session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM migration_records").fetchone()[0] == 1


def test_only_users_authority_is_registered_and_legacy_001010_is_unchanged():
    assert [(item.namespace, item.migration_key) for item in NAMESPACE_MIGRATIONS] == [
        ("foundation", "users_authority"),
        ("future", "entra_identity_bindings"),
        ("future", "approval_workflow"),
    ]
    assert [item.version for item in CONTROLLED_ANALYST_PILOT_MIGRATIONS] == list(range(1, 11))
