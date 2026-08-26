import sqlite3

import pytest

from database.backend import SQLiteBackend
from database.migration_conversion import ConversionError, convert_sqlite_core_data
from database.migration_runner import MigrationRunner
from database.schema import initialize_schema


def test_migration_runner_is_idempotent(tmp_path):
    backend = SQLiteBackend(tmp_path / "runner.sqlite")
    runner = MigrationRunner(backend)

    assert runner.run() == (1,)
    assert runner.run() == ()


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
