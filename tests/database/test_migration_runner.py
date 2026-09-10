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

    assert runner.run() == tuple(range(1, 9))
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

    assert versions == list(range(1, 9))
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
    } <= tables


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
