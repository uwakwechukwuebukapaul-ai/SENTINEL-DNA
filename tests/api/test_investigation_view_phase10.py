"""Phase 10 analyst investigation view API tests."""

from types import SimpleNamespace

from flask import Flask

from services.api.investigations.routes import investigations_api


def _app(view=None, metrics=None):
    app = Flask(__name__)
    app.testing = True
    coordinator = SimpleNamespace(get_investigation_view=lambda case_id, context: view, get_investigation_metrics=lambda case_id, context: metrics)
    app.container = SimpleNamespace(get=lambda name: coordinator)
    app.register_blueprint(investigations_api)
    return app


def test_investigation_view_returns_complete_projection():
    view = {"investigation": {"case_id": "CASE-10"}, "findings": [], "quality": {}, "feedback": []}
    response = _app(view).test_client().get("/api/investigations/CASE-10/view", headers={"X-Organization-ID": "tenant-a"})
    assert response.status_code == 200
    assert response.get_json() == view


def test_investigation_view_returns_not_found_without_projection():
    response = _app(None).test_client().get("/api/investigations/CASE-MISSING/view", headers={"X-Organization-ID": "tenant-a"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "investigation_not_found"}


def test_investigation_metrics_returns_read_only_quality_rates():
    metrics = {"acceptance_rate": 0.5, "false_positive_rate": 0.25, "feedback_count": 4}
    response = _app({"investigation": {"case_id": "CASE-10"}}, metrics).test_client().get("/api/investigations/CASE-10/metrics", headers={"X-Organization-ID": "tenant-a"})
    assert response.status_code == 200
    assert response.get_json() == metrics
