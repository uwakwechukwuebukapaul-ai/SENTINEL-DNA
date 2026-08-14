"""Focused tests for the production dashboard routes."""

import dashboard.app as dashboard_app


def make_client():
    dashboard_app.app.config["TESTING"] = True
    return dashboard_app.app.test_client()


def test_healthz_and_readyz_return_200(monkeypatch):
    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: {"ok": 1})
    client = make_client()

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_case_api_existing_case_returns_200(monkeypatch):
    case = {
        "case_id": "CASE-TEST-001",
        "title": "Test case",
        "severity": "HIGH",
        "description": "Test description",
        "status": "OPEN",
    }
    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: case.copy())
    monkeypatch.setattr(dashboard_app, "fetch_all", lambda *args: [])

    response = make_client().get("/api/cases/CASE-TEST-001")

    assert response.status_code == 200
    assert response.get_json()["case_id"] == "CASE-TEST-001"


def test_investigation_run_reaches_controller(monkeypatch):
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
    monkeypatch.setattr(dashboard_app, "fetch_one", lambda *args: {})

    response = make_client().get("/api/cases/MISSING")

    assert response.status_code == 404


def test_missing_case_id_returns_400():
    response = make_client().post("/api/investigations/run", json={})

    assert response.status_code == 400
