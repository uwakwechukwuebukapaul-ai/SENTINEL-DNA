from types import SimpleNamespace
from pathlib import Path
from flask import Flask, g
from dashboard.analyst_workspace import analyst_workspace
from services.api.investigations.routes import investigations_api


class Coordinator:
    intelligence_repository = SimpleNamespace(get_by_case_id=lambda case_id: {"metadata": {"tenant_id": "tenant-a"}})
    def get_report_by_case_id(self, case_id):
        return {"case_id": case_id, "summary": "safe <summary>", "findings": ["finding"], "tenant_context": {"tenant_id": "tenant-a"}}
    def get_feedback(self, case_id, tenant_id):
        return [{"decision": "accepted", "created_at": "2026-08-19T10:00:00+00:00"}]
    def get_feedback_analytics(self, tenant_id, **filters):
        period = "2026-08-17" if filters.get("granularity") == "weekly" else "2026-08-19"
        return {"total_feedback_events": 1, "counts": {"accepted": 1}, "rates": {"accepted_rate": 1.0}, "trends": [{"period_start": period, "total_feedback_events": 1}], "by_case": [{"id": "CASE-1", "total_feedback_events": 1, "latest_feedback_at": "2026-08-19T10:00:00+00:00"}], "by_investigation": [{"id": "INV-1", "total_feedback_events": 1, "latest_feedback_at": "2026-08-19T10:00:00+00:00"}]}


def app():
    root = Path(__file__).resolve().parents[2]
    application = Flask(__name__, template_folder=str(root / "dashboard" / "templates"))
    application.secret_key = "test"
    application.add_url_rule("/dashboard-static/<path:filename>", "dashboard_static", lambda filename: "")
    application.container = SimpleNamespace(require=lambda name: Coordinator())
    @application.before_request
    def context():
        g.security_context = SimpleNamespace(tenant_id="tenant-a", actor_id="actor-a")
    application.register_blueprint(analyst_workspace)
    application.register_blueprint(investigations_api)
    return application


def test_quality_view_is_advisory_and_escaped():
    response = app().test_client().get("/workspace/analyst/CASE-1")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Investigator Quality" in body
    assert "Total feedback events" in body
    assert "not model accuracy" in body
    assert "&lt;summary&gt;" in body
    assert "Weekly trend" in body
    assert "Investigation aggregation" in body
    assert "Content-Type': 'application/json'" in body


def test_workspace_is_read_only():
    assert app().test_client().post("/workspace/analyst/CASE-1").status_code == 405
