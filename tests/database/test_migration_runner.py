import sqlite3

import pytest

from database.backend import SQLiteBackend
from database.errors import DatabaseError
from database.migration_conversion import ConversionError, convert_sqlite_core_data
from database.migration_runner import Migration, MigrationRunner
from database.schema import initialize_schema


def test_migration_runner_is_idempotent(tmp_path):
    backend = SQLiteBackend(tmp_path / "runner.sqlite")
    runner = MigrationRunner(backend)

    assert runner.run() == tuple(range(1, 10))
    assert runner.run() == ()

    with backend.session() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        versions = [
            row[0]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]

    assert versions == list(range(1, 10))
    assert {
        "schema_migrations",
        "cases",
        "canonical_tenants",
        "canonical_memberships",
        "canonical_provider_tenant_trusts",
        "billing_customers",
        "crypto_payment_intents",
        "investigation_memory",
        "organizational_memory",
        "users",
        "mfa_sessions",
    } <= tables


def test_mfa_schema_is_authoritative_without_service_construction(tmp_path):
    backend = SQLiteBackend(tmp_path / "mfa-schema.sqlite")
    assert MigrationRunner(backend).run() == tuple(range(1, 10))

    with backend.session() as connection:
        before = {
            row["name"]: row["sql"]
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type IN ('table', 'index') AND name IN "
                "('mfa_sessions', 'idx_mfa_sessions_user_active')"
            ).fetchall()
        }

    from services.auth.mfa import MFAService

    MFAService(backend, secret_key_provider=lambda: "x" * 40)

    with backend.session() as connection:
        after = {
            row["name"]: row["sql"]
            for row in connection.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type IN ('table', 'index') AND name IN "
                "('mfa_sessions', 'idx_mfa_sessions_user_active')"
            ).fetchall()
        }

    assert set(before) == {"mfa_sessions", "idx_mfa_sessions_user_active"}
    assert after == before


def test_auth_service_does_not_create_authoritative_user_or_mfa_schema(tmp_path):
    backend = SQLiteBackend(tmp_path / "auth-without-migrations.sqlite")

    from services.auth.auth_service import AuthService

    AuthService(backend)

    with backend.session() as connection:
        authoritative_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('users', 'mfa_sessions')"
            ).fetchall()
        }

    assert authoritative_tables == set()


def test_auth_service_uses_schema_created_by_migration_009(tmp_path):
    backend = SQLiteBackend(tmp_path / "auth-after-migrations.sqlite")
    assert MigrationRunner(backend).run() == tuple(range(1, 10))

    from services.auth.auth_service import AuthService

    auth = AuthService(backend)
    user = auth.register(
        "migrated-user",
        "migrated-user@example.test",
        "migration-password",
        mfa_required=True,
    )

    with backend.session() as connection:
        row = connection.execute(
            "SELECT mfa_required, mfa_secret_ciphertext FROM users WHERE id=?",
            (user.id,),
        ).fetchone()
        mfa_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mfa_sessions'"
        ).fetchone()

    assert int(row["mfa_required"]) == 1
    assert row["mfa_secret_ciphertext"] is None
    assert mfa_table["name"] == "mfa_sessions"


def test_mfa_migration_upgrades_existing_users_table(tmp_path):
    backend = SQLiteBackend(tmp_path / "mfa-upgrade.sqlite")
    with backend.session() as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'analyst',
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )

    MigrationRunner(backend).run()

    with backend.session() as connection:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        mfa_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mfa_sessions'"
        ).fetchone()

    assert {
        "mfa_secret_ciphertext",
        "mfa_enrolled_at",
        "mfa_required",
        "mfa_last_counter",
    } <= columns
    assert mfa_table["name"] == "mfa_sessions"


def test_migration_runner_rolls_back_failed_migration(tmp_path):
    backend = SQLiteBackend(tmp_path / "rollback.sqlite")
    migrations = (
        Migration(
            1,
            "transactional_failure",
            statements=lambda _backend: (
                "CREATE TABLE migration_probe (value TEXT)",
                "THIS IS NOT VALID SQL",
            ),
        ),
    )

    with pytest.raises(DatabaseError):
        MigrationRunner(backend, migrations=migrations).run()

    with backend.session() as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone() is None
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migration_probe'"
        ).fetchone() is None


def test_sqlite_core_conversion_preserves_counts_and_rejects_noncanonical_source(tmp_path):
    source = tmp_path / "source.sqlite"
    source_backend = SQLiteBackend(source)
    initialize_schema(source_backend)
    with source_backend.session() as connection:
        connection.execute(
            "INSERT INTO cases(case_id, title, severity, created) VALUES (?, ?, ?, ?)",
            ("case-1", "Test case", "HIGH", "2026-08-26T00:00:00+00:00"),
        )

    target = SQLiteBackend(tmp_path / "target.sqlite")
    initialize_schema(target)
    report = convert_sqlite_core_data(source, target)

    assert report.row_counts["cases"] == 1
    assert report.row_counts["case_notes"] == 0
    with target.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1

    legacy = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(legacy)
    connection.execute("CREATE TABLE cases (id INTEGER PRIMARY KEY, case_id TEXT)")
    connection.commit()
    connection.close()
    with pytest.raises(ConversionError, match="source_tables_missing"):
        convert_sqlite_core_data(legacy, target)
