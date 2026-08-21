import sqlite3

import pytest

from database.errors import DatabaseError
from services.dashboard.dashboard_service import DashboardService


def test_metrics_and_intelligence_projection(tmp_path):
    path = tmp_path / "soc.db"

    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE cases (
            id INTEGER PRIMARY KEY,
            case_id TEXT,
            title TEXT,
            severity TEXT,
            status TEXT,
            created TEXT
        );

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
        );

        CREATE TABLE timeline (
            id INTEGER PRIMARY KEY,
            case_id TEXT,
            event_type TEXT,
            description TEXT,
            actor TEXT,
            created TEXT
        );

        INSERT INTO cases
        VALUES
        (1,'C-1','Phishing','HIGH','OPEN','now');

        INSERT INTO cases
        VALUES
        (2,'C-2','Malware','LOW','COMPLETED','later');

        INSERT INTO iocs
        VALUES
        (1,'IOC-1','C-1','DOMAIN','evil.example','HIGH','MALICIOUS','TEST','now');

        INSERT INTO timeline
        VALUES
        (1,'C-1','ALERT','IOC observed','SYSTEM','now');
        """)

    snapshot = DashboardService(path).snapshot()

    assert snapshot.metrics["total_cases"] == 2
    assert snapshot.metrics["active_investigations"] == 1
    assert snapshot.metrics["critical_high_cases"] == 1
    assert snapshot.iocs[0]["value"] == "evil.example"


def test_dashboard_route_requires_authentication(monkeypatch):
    import dashboard.app as dashboard_app

    dashboard_app.app.config["TESTING"] = True

    with dashboard_app.app.test_client() as client:
        response = client.get("/workspace/dashboard")

        assert response.status_code == 401


def _write_ioc_database(path, *, legacy=False, value="evil.example"):
    ioc_columns = (
        "id INTEGER PRIMARY KEY, ioc_id TEXT UNIQUE NOT NULL, "
        "case_id TEXT NOT NULL, ioc_type TEXT NOT NULL, value TEXT NOT NULL, "
        "confidence TEXT, reputation TEXT, source TEXT, created TEXT NOT NULL"
        if not legacy
        else "id INTEGER PRIMARY KEY, case_id TEXT, type TEXT, value TEXT, created TEXT"
    )
    with sqlite3.connect(path) as db:
        db.executescript(
            f"""
            CREATE TABLE cases (
                id INTEGER PRIMARY KEY,
                case_id TEXT,
                title TEXT,
                severity TEXT,
                status TEXT,
                created TEXT
            );
            CREATE TABLE iocs ({ioc_columns});
            CREATE TABLE timeline (
                id INTEGER PRIMARY KEY,
                case_id TEXT,
                event_type TEXT,
                description TEXT,
                actor TEXT,
                created TEXT
            );
            INSERT INTO cases VALUES (1, 'C-1', 'Test', 'HIGH', 'OPEN', 'now');
            """
        )
        if legacy:
            db.execute("INSERT INTO iocs VALUES (1, 'C-1', 'DOMAIN', ?, 'now')", (value,))
        else:
            db.execute(
                "INSERT INTO iocs VALUES (1, 'IOC-1', 'C-1', 'DOMAIN', ?, 'HIGH', 'MALICIOUS', 'TEST', 'now')",
                (value,),
            )


def test_dashboard_service_uses_configured_canonical_database(monkeypatch, tmp_path):
    configured = tmp_path / "configured.db"
    _write_ioc_database(configured, value="configured.example")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(configured))

    snapshot = DashboardService().snapshot()

    assert snapshot.iocs[0]["value"] == "configured.example"


def test_dashboard_service_explicit_database_path_overrides_environment(monkeypatch, tmp_path):
    configured = tmp_path / "configured.db"
    explicit = tmp_path / "explicit.db"
    _write_ioc_database(configured, value="configured.example")
    _write_ioc_database(explicit, value="explicit.example")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(configured))

    snapshot = DashboardService(explicit).snapshot()

    assert snapshot.iocs[0]["value"] == "explicit.example"


def test_dashboard_service_rejects_retired_ioc_schema(tmp_path):
    legacy = tmp_path / "legacy.db"
    _write_ioc_database(legacy, legacy=True)

    with pytest.raises(DatabaseError):
        DashboardService(legacy).snapshot()
