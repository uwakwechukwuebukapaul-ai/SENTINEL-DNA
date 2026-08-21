import inspect
import sqlite3

from database.connection import resolve_database_path
from services.hunting import HuntEngine, HuntQuery, HuntRepository
from services.hunting.engine import HuntEngine as ConcreteHuntEngine

def test_ioc_hunting_and_persistence(tmp_path):
    path = tmp_path / "hunt.db"
    with sqlite3.connect(path) as db:
        db.execute("""
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY,
                ioc_id TEXT UNIQUE NOT NULL,
                case_id TEXT NOT NULL,
                ioc_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence TEXT,
                reputation TEXT,
                source TEXT,
                created TEXT NOT NULL
            )
        """)
        db.execute("INSERT INTO iocs VALUES (1,'IOC-1','CASE-1','domain','evil.example','HIGH','UNKNOWN','TEST','now')")
    result = HuntEngine(str(path)).execute(HuntQuery("evil.example"))
    assert result.status.value == "completed" and result.findings[0].case_id == "CASE-1"
    repo = HuntRepository(str(path)); repo.save(result)
    assert repo.get(result.hunt_id)["findings"][0]["value"] == "evil.example"

def test_behavior_hunting(tmp_path):
    path = tmp_path / "hunt.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE cases (case_id TEXT,title TEXT,severity TEXT,status TEXT)")
        db.execute("INSERT INTO cases VALUES ('CASE-2','Suspicious login','high','open')")
    assert HuntEngine(str(path)).execute(HuntQuery("suspicious", "behavior")).findings


def _create_ioc_database(path, value):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE iocs (id INTEGER PRIMARY KEY, ioc_id TEXT UNIQUE NOT NULL, case_id TEXT NOT NULL, ioc_type TEXT NOT NULL, value TEXT NOT NULL, confidence TEXT, reputation TEXT, source TEXT, created TEXT NOT NULL)")
        db.execute("INSERT INTO iocs VALUES (1,'IOC-1','CASE-1','domain',?,'HIGH','UNKNOWN','TEST','now')", (value,))


def test_hunt_engine_uses_configured_database_path(monkeypatch, tmp_path):
    path = tmp_path / "configured-hunt.db"
    _create_ioc_database(path, "configured.example")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(path))

    engine = HuntEngine()

    assert engine.db_path == str(resolve_database_path())
    assert engine.execute(HuntQuery("configured.example")).findings[0].case_id == "CASE-1"


def test_hunt_engine_explicit_path_overrides_environment(monkeypatch, tmp_path):
    configured = tmp_path / "configured.db"
    explicit = tmp_path / "explicit.db"
    _create_ioc_database(configured, "configured.example")
    _create_ioc_database(explicit, "explicit.example")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(configured))

    result = HuntEngine(explicit).execute(HuntQuery("explicit.example"))

    assert result.findings[0].value == "explicit.example"


def test_hunt_engine_rejects_legacy_ioc_schema(tmp_path):
    path = tmp_path / "legacy-hunt.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE iocs (case_id TEXT, type TEXT, value TEXT)")
        db.execute("INSERT INTO iocs VALUES ('CASE-1','domain','legacy.example')")

    result = HuntEngine(path).execute(HuntQuery("legacy.example"))

    assert result.status.value == "failed"
    assert result.error == "DatabaseError"


def test_hunt_engine_has_no_direct_ioc_sql():
    source = inspect.getsource(ConcreteHuntEngine)

    assert "FROM iocs" not in source
    assert "INSERT INTO iocs" not in source
