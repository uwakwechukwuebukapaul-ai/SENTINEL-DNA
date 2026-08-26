import pytest

from database.backend import (
    DatabaseConfigurationError,
    DatabaseSettings,
    PostgreSQLBackend,
    SQLiteBackend,
    create_database_backend,
)
from database.connection import DatabaseConnection, database_for_environment


def test_database_url_is_authoritative_over_sqlite_path():
    settings = DatabaseSettings.from_environment(
        {
            "DATABASE_URL": "postgresql://sentinel:secret@db.example/sentinel",
            "SENTINEL_DNA_DB_PATH": "ignored.sqlite",
        }
    )

    assert settings.backend == "postgresql"
    assert settings.database_url.startswith("postgresql://")
    assert settings.database_path is None
    assert isinstance(
        create_database_backend(
            environ={
                "DATABASE_URL": "postgresql://sentinel:secret@db.example/sentinel",
                "SENTINEL_DNA_DB_PATH": "ignored.sqlite",
            }
        ),
        PostgreSQLBackend,
    )


def test_sqlite_remains_the_nonproduction_default(tmp_path):
    backend = create_database_backend(
        environ={"SENTINEL_DNA_DB_PATH": str(tmp_path / "local.sqlite")}
    )
    assert isinstance(backend, SQLiteBackend)
    with backend.session() as connection:
        connection.execute("CREATE TABLE probe (value TEXT NOT NULL)")
        connection.execute("INSERT INTO probe VALUES (?)", ("ok",))
    with backend.session() as connection:
        assert connection.execute("SELECT value FROM probe").fetchone()[0] == "ok"


def test_production_backend_resolution_fails_closed_without_postgresql_url():
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL"):
        create_database_backend(
            environ={"SENTINEL_DNA_ENV": "production", "SENTINEL_DNA_DB_PATH": "soc.db"},
            require_postgresql=True,
        )


def test_production_process_backend_resolution_fails_closed_without_postgresql_url(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "soc.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL"):
        database_for_environment()


def test_legacy_database_connection_with_explicit_path_is_sqlite(tmp_path):
    backend = DatabaseConnection(tmp_path / "legacy.sqlite")
    assert isinstance(backend, SQLiteBackend)
