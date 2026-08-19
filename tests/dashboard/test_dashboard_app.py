"""Focused tests for the production dashboard routes."""

import sqlite3

import dashboard.app as dashboard_app
import services.auth.permissions as permissions
from services.cases.case_service import AuthorizedCaseAccess
from services.intelligence.ioc.persistence_service import IOCAccessContext
from services.intelligence.ioc.persistence_service import IOCAccessDenied


def make_client():
    dashboard_app.app.config["TESTING"] = True
    return dashboard_app.app.test_client()


def authorize_dashboard_case(monkeypatch, case_id):
    monkeypatch.setattr(permissions, "current_role", lambda: "admin")
    monkeypatch.setattr(dashboard_app, "current_role", lambda: "admin")
    monkeypatch.setattr(
        dashboard_app,
        "authorized_ioc_context",
        lambda requested_case_id: IOCAccessContext.from_authorized_case(
            AuthorizedCaseAccess(requested_case_id, 1, "admin")
        ),
    )


def test_healthz_and_readyz_return_200(monkeypatch):
    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: {"ok": 1})
    client = make_client()

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_global_dashboard_ioc_routes_require_existing_rbac(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: None)
    monkeypatch.setattr(dashboard_app, "current_role", lambda: None)

    client = make_client()

    assert client.get("/").status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/workspace").status_code == 401
    assert client.get("/workspace/iocs").status_code == 401


def test_global_dashboard_ioc_route_uses_existing_read_permission(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: "analyst")
    monkeypatch.setattr(dashboard_app, "current_role", lambda: "analyst")
    monkeypatch.setattr(dashboard_app, "dashboard_payload", lambda: {"iocs": []})

    response = make_client().get("/api/dashboard")

    assert response.status_code == 200


def test_case_api_existing_case_returns_200(monkeypatch):
    authorize_dashboard_case(monkeypatch, "CASE-TEST-001")
    case = {
        "case_id": "CASE-TEST-001",
        "title": "Test case",
        "severity": "HIGH",
        "description": "Test description",
        "status": "OPEN",
    }
    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: case.copy())
    monkeypatch.setattr(dashboard_app, "fetch_all", lambda *args: [])
    monkeypatch.setattr(
        dashboard_app,
        "ioc_data_access",
        lambda: type("IOCStub", (), {"case_records": lambda self, *args, **kwargs: []})(),
    )

    response = make_client().get("/api/cases/CASE-TEST-001")

    assert response.status_code == 200
    assert response.get_json()["case_id"] == "CASE-TEST-001"


def test_investigation_run_reaches_controller(monkeypatch):
    authorize_dashboard_case(monkeypatch, "CASE-TEST-001")
    case = {
        "case_id": "CASE-TEST-001",
        "title": "Test case",
        "severity": "HIGH",
        "description": "Test description",
        "status": "OPEN",
    }
    calls = {}
    evidence = [{"id": 1, "type": "LOG FILE", "data": "event", "sha256": "abc", "created": "now"}]
    iocs = [{"id": 2, "type": "IP ADDRESS", "value": "185.22.45.100", "created": "now"}]
    timeline = [{"id": 3, "event_type": "ALERT", "description": "IOC observed", "actor": "analyst", "created": "now"}]

    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: case.copy())

    def fetch_all(sql, params=()):
        if "FROM evidence" in sql:
            return evidence
        if "FROM iocs" in sql:
            return iocs
        if "FROM timeline" in sql:
            return timeline
        return []

    monkeypatch.setattr(dashboard_app, "fetch_all", fetch_all)

    class FakeIOCDataAccess:
        def list_for_case(self, case_id, *, context):
            return [
                {
                    "id": 2,
                    "ioc_id": "IOC-TEST-002",
                    "case_id": case_id,
                    "ioc_type": "IP ADDRESS",
                    "value": "185.22.45.100",
                    "confidence": "HIGH",
                    "reputation": "UNKNOWN",
                    "source": "TEST",
                    "created": "now",
                }
            ]

    monkeypatch.setattr(dashboard_app, "ioc_data_access", FakeIOCDataAccess)

    class FakeController:
        def __init__(self, coordinator):
            calls["coordinator"] = coordinator

        def run(self, artifacts, case_id, alert, **context):
            calls["request"] = (artifacts, case_id, alert, context)
            return {"success": True, "status": "completed"}

    monkeypatch.setattr(dashboard_app, "InvestigationController", FakeController)

    response = make_client().post(
        "/api/investigations/run",
        json={"case_id": "CASE-TEST-001"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert calls["coordinator"] is dashboard_app.app.container.get(
        "investigation_coordinator"
    )
    assert calls["request"][1] == "CASE-TEST-001"
    assert calls["request"][0] == [
        {"type": "LOG FILE", "data": "event", "created": "now"}
    ]
    assert calls["request"][3] == {
        "evidence": evidence,
        "iocs": iocs,
        "timeline": timeline,
    }


def test_missing_case_returns_404(monkeypatch):
    authorize_dashboard_case(monkeypatch, "MISSING")
    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: {})

    response = make_client().get("/api/cases/MISSING")

    assert response.status_code == 404


def test_missing_case_id_returns_400(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: "admin")
    monkeypatch.setattr(dashboard_app, "current_role", lambda: "admin")
    response = make_client().post("/api/investigations/run", json={})

    assert response.status_code == 400


def test_case_api_requires_authenticated_case_access(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: None)
    monkeypatch.setattr(dashboard_app, "current_role", lambda: None)

    response = make_client().get("/api/cases/CASE-A")

    assert response.status_code == 401


def test_case_url_change_cannot_bypass_authoritative_case_access(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: "analyst")
    monkeypatch.setattr(dashboard_app, "current_role", lambda: "analyst")
    authorized = IOCAccessContext.from_authorized_case(
        AuthorizedCaseAccess("CASE-A", 7, "analyst")
    )

    def context_for_case(case_id):
        if case_id != "CASE-A":
            raise IOCAccessDenied("case_access_denied")
        return authorized

    monkeypatch.setattr(dashboard_app, "authorized_ioc_context", context_for_case)

    response = make_client().get("/api/cases/CASE-B")

    assert response.status_code == 403


def test_investigation_route_denies_unauthorized_case(monkeypatch):
    authorize_dashboard_case(monkeypatch, "CASE-A")
    monkeypatch.setattr(
        dashboard_app,
        "authorized_ioc_context",
        lambda case_id: (_ for _ in ()).throw(IOCAccessDenied("case_access_denied")),
    )

    response = make_client().post(
        "/api/investigations/run",
        json={"case_id": "CASE-B"},
    )

    assert response.status_code == 403


def test_canonical_ioc_consumers_use_migrated_schema(tmp_path, monkeypatch):
    authorize_dashboard_case(monkeypatch, "CASE-CANONICAL-001")
    database_path = tmp_path / "canonical-dashboard.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (
                id INTEGER PRIMARY KEY,
                case_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                analyst TEXT,
                created TEXT NOT NULL
            );
            CREATE TABLE evidence (
                id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                sha256 TEXT,
                created TEXT NOT NULL
            );
            CREATE TABLE timeline (
                id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                actor TEXT NOT NULL,
                created TEXT NOT NULL
            );
            CREATE TABLE analyst_actions (
                id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                action TEXT NOT NULL,
                analyst TEXT NOT NULL,
                created TEXT NOT NULL
            );
            CREATE TABLE case_notes (
                id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                analyst TEXT NOT NULL,
                note TEXT NOT NULL,
                created TEXT NOT NULL
            );
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY,
                ioc_id TEXT UNIQUE NOT NULL,
                case_id TEXT NOT NULL,
                ioc_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence TEXT NOT NULL,
                reputation TEXT NOT NULL,
                source TEXT NOT NULL,
                created TEXT NOT NULL
            );
            INSERT INTO cases VALUES
                (1, 'CASE-CANONICAL-001', 'Canonical IOC', 'HIGH',
                 'Test case', 'OPEN', 'analyst', 'now');
            INSERT INTO iocs VALUES
                (1, 'IOC-CANONICAL-001', 'CASE-CANONICAL-001', 'DOMAIN',
                 'evil.example', 'HIGH', 'MALICIOUS', 'TEST', 'now');
            """
        )

    monkeypatch.setattr(dashboard_app, "DB_PATH", database_path)
    client = make_client()

    dashboard_result = dashboard_app.dashboard_payload()
    assert dashboard_result["iocs"][0]["ioc_type"] == "DOMAIN"

    workspace_response = client.get("/workspace/iocs")
    assert workspace_response.status_code == 200
    assert b"DOMAIN" in workspace_response.data

    case_response = client.get("/api/cases/CASE-CANONICAL-001")
    assert case_response.status_code == 200
    assert case_response.get_json()["iocs"] == [
        {
            "id": 1,
            "ioc_id": "IOC-CANONICAL-001",
            "ioc_type": "DOMAIN",
            "value": "evil.example",
            "confidence": "HIGH",
            "reputation": "MALICIOUS",
            "source": "TEST",
            "created": "now",
        }
    ]

    captured = {}

    class FakeController:
        def __init__(self, coordinator):
            self.coordinator = coordinator

        def run(self, artifacts, case_id, alert, **context):
            captured["iocs"] = context["iocs"]
            return {"success": True}

    monkeypatch.setattr(dashboard_app, "InvestigationController", FakeController)
    investigation_response = client.post(
        "/api/investigations/run",
        json={"case_id": "CASE-CANONICAL-001"},
    )
    assert investigation_response.status_code == 200
    assert captured["iocs"] == [
        {
            "id": 1,
            "type": "DOMAIN",
            "value": "evil.example",
            "created": "now",
        }
    ]
