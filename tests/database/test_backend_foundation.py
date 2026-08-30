import pytest
import sys
import types

from database.backend import (
    DatabaseConfigurationError,
    DatabaseError,
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


def test_sqlite_health_check_uses_backend_contract(tmp_path):
    backend = SQLiteBackend(tmp_path / "health.sqlite")
    assert backend.health_check() is True


def test_production_backend_resolution_fails_closed_without_postgresql_url():
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL"):
        create_database_backend(
            environ={"SENTINEL_DNA_ENV": "production", "SENTINEL_DNA_DB_PATH": "soc.db"},
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


def test_explicit_sqlite_path_remains_compatible_in_production_shaped_environment(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    backend = DatabaseConnection(tmp_path / "compatibility.sqlite")

    assert isinstance(backend, SQLiteBackend)


def test_postgresql_missing_driver_fails_without_network(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", None)
    with pytest.raises(DatabaseError, match="PostgreSQL driver is unavailable"):
        PostgreSQLBackend("postgresql://user:pw@db.example/sentinel").connect()


def test_postgresql_session_commits_and_closes(monkeypatch):
    class FakeError(Exception):
        pass

    class FakeConnection:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
            self.closed = False

        def execute(self, query):
            assert query == "SELECT 1 AS health_probe"
            return self

        def fetchone(self):
            return {"health_probe": 1}

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closed = True

    connections = []
    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.Error = FakeError
    fake_psycopg.connect = lambda *args, **kwargs: connections.append(FakeConnection()) or connections[-1]
    fake_rows = types.ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)

    backend = PostgreSQLBackend("postgresql://user:pw@db.example/sentinel")
    assert backend.health_check() is True
    assert connections[-1].commits == 1
    assert connections[-1].rollbacks == 0
    assert connections[-1].closed is True


def test_postgresql_backend_consumes_password_file_without_environment_password(monkeypatch, tmp_path):
    class FakeConnection:
        def execute(self, query):
            assert query == "SELECT 1 AS health_probe"
            return self

        def fetchone(self):
            return {"health_probe": 1}

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    connection = FakeConnection()
    observed = {}
    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.Error = RuntimeError

    def connect(*args, **kwargs):
        observed.update(kwargs)
        return connection

    fake_psycopg.connect = connect
    fake_rows = types.ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)
    password = "p" * 40
    password_file = tmp_path / "postgres-password"
    password_file.write_text(password + "\n", encoding="utf-8")

    backend = PostgreSQLBackend(
        "postgresql://sentinel@db.example/sentinel",
        password_file=password_file,
    )

    assert backend.health_check() is True
    assert observed["password"] == password


def test_postgresql_adapter_translates_legacy_repository_sql(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.statements = []
            self.closed = False

        def execute(self, statement, params=()):
            self.statements.append((statement, params))
            return self

        def fetchone(self):
            return {"health_probe": 1}

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    connection = FakeConnection()
    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.Error = RuntimeError
    fake_psycopg.connect = lambda *args, **kwargs: connection
    fake_rows = types.ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)

    with PostgreSQLBackend("postgresql://user:pw@db.example/sentinel").session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("SELECT * FROM cases WHERE case_id=?", ("case-1",))

    assert connection.statements == [
        ("BEGIN", ()),
        ("SELECT * FROM cases WHERE case_id=%s", ("case-1",)),
    ]


def test_postgresql_session_rolls_back_and_closes_on_application_error(monkeypatch):
    class FakeError(Exception):
        pass

    class FakeConnection:
        def __init__(self):
            self.rollbacks = 0
            self.closed = False

        def commit(self):
            raise AssertionError("commit must not run after an application error")

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closed = True

    connection = FakeConnection()
    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.Error = FakeError
    fake_psycopg.connect = lambda *args, **kwargs: connection
    fake_rows = types.ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)

    with pytest.raises(ValueError, match="application failure"):
        with PostgreSQLBackend("postgresql://user:pw@db.example/sentinel").session():
            raise ValueError("application failure")
    assert connection.rollbacks == 1
    assert connection.closed is True
