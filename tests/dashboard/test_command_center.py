import sqlite3

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
            case_id TEXT,
            ioc_type TEXT,
            value TEXT,
            confidence TEXT,
            created TEXT
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
        (1,'C-1','DOMAIN','evil.example','HIGH','now');

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