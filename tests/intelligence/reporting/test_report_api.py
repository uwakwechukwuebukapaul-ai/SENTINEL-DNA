"""
Sentinel DNA Report API Tests

Validates investigation report API endpoints.

Coverage:

- report generation endpoint
- report retrieval endpoint
- response schema
- report persistence boundary
"""

from __future__ import annotations

import pytest
from tests.credential_helpers import random_token
from types import SimpleNamespace

from flask import Flask

from services.api.investigation_routes import (
    investigation_bp,
)
from services.api.investigations.routes import investigations_api
from services.api.investigations.routes import _execute_investigation
from services.intelligence.reporting.investigation_report import InvestigationReport


@pytest.fixture
def client():

    app = Flask(
        __name__
    )

    app.register_blueprint(
        investigation_bp
    )

    app.testing = True

    return app.test_client()



def test_generate_investigation_report(
    client,
):

    response = client.post(
        "/api/investigations/report",
        json={
            "case_id": "CASE-001",
            "alert": {
                "source": "email",
                "indicator": "malicious-domain.xyz",
                "severity": "high",
            },
        },
    )


    assert response.status_code == 200


    data = response.get_json()


    assert data is not None


    assert "report" in data


    report = data["report"]


    assert (
        report["case_id"]
        ==
        "CASE-001"
    )


    assert (
        "severity"
        in report
    )


    assert (
        "findings"
        in report
    )



def test_get_investigation_report(
    client,
):

    response = client.get(
        "/api/investigations/report/CASE-001"
    )


    assert response.status_code in (
        200,
        404,
    )


    if response.status_code == 200:

        data = response.get_json()


        assert (
            "report"
            in data
        )


def test_canonical_investigation_api_projects_complete_report(monkeypatch):
    report = InvestigationReport(
        case_id="CASE-CANONICAL",
        summary="Evidence-backed investigation summary.",
        status="completed",
        risk={"score": 80, "severity": "high"},
        findings=[{"finding_id": "RF-1", "evidence_refs": ["E-1"]}],
        evidence=[{"evidence_id": "E-1"}],
        threat_intelligence={"status": "available"},
        intelligence_disposition={"status": [], "disposition": "supporting"},
        mitre=["T1566"],
        timeline=[{"event": "email received"}],
        reasoning={"summary": "Evidence supports review."},
        recommendations=["Escalate for analyst review"],
        governance={
            "mode": "ADVISORY_ONLY",
            "analyst_authority_required": True,
            "autonomous_action": False,
        },
        confidence=0.88,
        uncertainty="unknown",
        tenant_context={"tenant_id": "tenant-a", "actor_id": "actor-a"},
    )

    class Repository:
        def get_by_case_id(self, case_id):
            return {"case_id": case_id, "tenant_context": {"tenant_id": "tenant-a"}}

    class Coordinator:
        intelligence_repository = Repository()

        def get_report_by_case_id(self, case_id):
            return report if case_id == "CASE-CANONICAL" else None

    app = Flask(__name__)
    app.container = SimpleNamespace(get=lambda name: Coordinator())
    app.register_blueprint(investigations_api)
    monkeypatch.setattr(
        "services.api.investigations.routes.authorize_investigation",
        lambda *_args, **_kwargs: (True, None),
    )

    response = app.test_client().get("/api/investigations/CASE-CANONICAL")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["report"]["summary"] == "Evidence-backed investigation summary."
    assert payload["report"]["findings"][0]["evidence_refs"] == ["E-1"]
    assert payload["report"]["governance"]["mode"] == "ADVISORY_ONLY"
    assert payload["report"]["recommendations"] == ["Escalate for analyst review"]


def _execution_app(coordinator):
    app = Flask(__name__)
    app.testing = True
    app.container = SimpleNamespace(get=lambda name: coordinator)
    app.register_blueprint(investigations_api)
    return app


def test_unexpected_investigation_failure_returns_safe_json_500(monkeypatch):
    secret_token = random_token()
    class Coordinator:
        def investigate(self, **kwargs):
            raise RuntimeError(f"{secret_token} / raw-provider-response")

    app = _execution_app(Coordinator())
    monkeypatch.setattr("services.api.investigations.routes.authorize_investigation", lambda *_a, **_k: (True, ""))
    response = app.test_client().post("/api/investigations", json={"case_id": "CASE-FAIL", "alert": {}})

    assert response.status_code == 500
    assert response.is_json
    assert response.get_json() == {"error": {"code": "INVESTIGATION_EXECUTION_FAILED", "message": "Investigation execution failed"}}
    assert "traceback" not in response.get_data(as_text=True).lower()
    assert secret_token not in response.get_data(as_text=True)
    assert "raw-provider-response" not in response.get_data(as_text=True)


def test_permission_error_is_not_converted_to_generic_500(monkeypatch):
    class Coordinator:
        def investigate(self, **kwargs):
            raise PermissionError("actor is not authorized for threat intelligence lookup")

    app = _execution_app(Coordinator())
    monkeypatch.setattr("services.api.investigations.routes.authorize_investigation", lambda *_a, **_k: (True, ""))

    with pytest.raises(PermissionError, match="actor is not authorized"):
        app.test_client().post("/api/investigations", json={"case_id": "CASE-AUTH", "alert": {}})


def test_observability_failure_does_not_change_safe_error(monkeypatch):
    class Coordinator:
        def investigate(self, **kwargs):
            raise RuntimeError("internal failure")

    class BrokenObserver:
        def event(self, *args, **kwargs):
            raise RuntimeError("telemetry failure")

    app = _execution_app(Coordinator())
    monkeypatch.setattr("services.api.investigations.routes.authorize_investigation", lambda *_a, **_k: (True, ""))
    monkeypatch.setattr("services.api.investigations.routes.ObservabilityService", BrokenObserver)
    response = app.test_client().post("/api/investigations", json={"case_id": "CASE-OBS", "alert": {}})

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "INVESTIGATION_EXECUTION_FAILED"
