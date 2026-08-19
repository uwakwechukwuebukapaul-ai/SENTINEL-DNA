import importlib.util
import sqlite3
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "database"
    / "migrations"
    / "migrate_ioc_contract.py"
)


def load_migration(monkeypatch, database_path):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(database_path))
    spec = importlib.util.spec_from_file_location(
        "ioc_contract_migration_test_module",
        MIGRATION_PATH,
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def create_legacy_database(database_path, *, value="evil.example"):
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL
            );
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY,
                case_id TEXT,
                type TEXT,
                value TEXT,
                created TEXT
            );
            INSERT INTO cases VALUES ('INC-001', 'IOC migration test');
            """
        )
        connection.execute(
            "INSERT INTO iocs VALUES (?, ?, ?, ?, ?)",
            (7, "INC-001", "DOMAIN", value, "2026-08-19T00:00:00"),
        )


def test_migrates_legacy_iocs_using_configured_database(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    create_legacy_database(database_path)
    migration = load_migration(monkeypatch, database_path)

    migration.migrate()

    with sqlite3.connect(database_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(iocs)")]
        row = connection.execute(
            "SELECT * FROM iocs"
        ).fetchone()
        registry = connection.execute(
            "SELECT case_id, ioc_type, value, ioc_id "
            "FROM ioc_duplicate_keys"
        ).fetchone()

    assert columns == migration.CANONICAL_COLUMNS
    assert row == (
        7,
        migration.generate_migrated_ioc_id(7),
        "INC-001",
        "DOMAIN",
        "evil.example",
        "MEDIUM",
        "UNKNOWN",
        "LEGACY_MIGRATION",
        "2026-08-19T00:00:00",
    )
    assert registry == ("INC-001", "DOMAIN", "evil.example", row[1])


def test_invalid_legacy_data_rolls_back_without_replacing_table(tmp_path, monkeypatch):
    database_path = tmp_path / "invalid.db"
    create_legacy_database(database_path, value="")
    migration = load_migration(monkeypatch, database_path)

    try:
        migration.migrate()
    except RuntimeError as error:
        assert "empty" in str(error)
    else:
        raise AssertionError("invalid legacy IOC data should fail migration")

    with sqlite3.connect(database_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(iocs)")]
        row = connection.execute("SELECT * FROM iocs").fetchone()

    assert columns == migration.EXPECTED_LEGACY_COLUMNS
    assert row == (7, "INC-001", "DOMAIN", "", "2026-08-19T00:00:00")


def test_canonical_schema_rerun_is_successful_and_unchanged(tmp_path, monkeypatch):
    database_path = tmp_path / "canonical.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL
            );
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY,
                ioc_id TEXT UNIQUE NOT NULL,
                case_id TEXT NOT NULL,
                ioc_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence TEXT DEFAULT 'MEDIUM',
                reputation TEXT DEFAULT 'UNKNOWN',
                source TEXT DEFAULT 'LOCAL',
                created TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(case_id)
            );
            INSERT INTO cases VALUES ('INC-001', 'IOC migration test');
            INSERT INTO iocs VALUES
                (7, 'IOC-EXISTING', 'INC-001', 'DOMAIN', 'evil.example',
                 'HIGH', 'MALICIOUS', 'TEST', '2026-08-19T00:00:00');
            """
        )

    migration = load_migration(monkeypatch, database_path)
    migration.migrate()

    with sqlite3.connect(database_path) as connection:
        snapshot = connection.execute("SELECT * FROM iocs").fetchall()
        registry = connection.execute(
            "SELECT case_id, ioc_type, value, ioc_id "
            "FROM ioc_duplicate_keys"
        ).fetchall()

    assert snapshot == [
        (7, "IOC-EXISTING", "INC-001", "DOMAIN", "evil.example",
         "HIGH", "MALICIOUS", "TEST", "2026-08-19T00:00:00")
    ]
    assert registry == [("INC-001", "DOMAIN", "evil.example", "IOC-EXISTING")]


def test_missing_ioc_table_fails_without_creating_legacy_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "missing.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE cases (case_id TEXT PRIMARY KEY, title TEXT NOT NULL)"
        )

    migration = load_migration(monkeypatch, database_path)

    try:
        migration.migrate()
    except RuntimeError as error:
        assert "IOC table does not exist" in str(error)
    else:
        raise AssertionError("missing IOC table should fail migration")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='iocs'"
        ).fetchone() is None
