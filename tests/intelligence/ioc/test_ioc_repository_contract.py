import sqlite3

from database.connection import database
from database.repository import add_ioc


def test_add_ioc_writes_canonical_contract(tmp_path):
    database_path = tmp_path / "ioc-repository.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL
            );
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            INSERT INTO cases VALUES ('INC-001', 'IOC repository test');
            """
        )

    previous_path = database.database_path
    database.database_path = str(database_path)
    try:
        assert add_ioc(
            "INC-001",
            "DOMAIN",
            "evil.example",
            confidence="HIGH",
            reputation="MALICIOUS",
            source="TEST",
        ) is True
    finally:
        database.database_path = previous_path

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT ioc_id, case_id, ioc_type, value,
                   confidence, reputation, source
            FROM iocs
            """
        ).fetchone()

    assert row[0].startswith("IOC-")
    assert row[1:] == (
        "INC-001",
        "DOMAIN",
        "evil.example",
        "HIGH",
        "MALICIOUS",
        "TEST",
    )
