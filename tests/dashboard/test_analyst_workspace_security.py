from types import SimpleNamespace
from pathlib import Path

from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader

from dashboard.analyst_workspace import analyst_workspace


class Repository:
    def get_by_case_id(self, case_id):
        return {"case_id": case_id, "metadata": {"tenant_id": "tenant-a"}}


class Coordinator:
    intelligence_repository = Repository()

    def get_report_by_case_id(self, case_id):
        return {
            "case_id": case_id,
            "tenant_context": {"tenant_id": "tenant-a"},
            "summary": "Evidence-backed report",
        }


def make_app():
    root = Path(__file__).resolve().parents[2]
    app = Flask(__name__, template_folder=str(root / "dashboard" / "templates"))
    app.jinja_loader = ChoiceLoader(
        [
            app.jinja_loader,
            FileSystemLoader(str(root / "dashboard" / "workspace" / "templates")),
        ]
    )
    app.add_url_rule(
        "/dashboard-static/<path:filename>",
        endpoint="dashboard_static",
        view_func=lambda filename: "",
    )
    app.secret_key = "test-secret"
    app.container = SimpleNamespace(require=lambda name: Coordinator())
    app.register_blueprint(analyst_workspace)
    return app


def test_workspace_requires_server_side_authorization(monkeypatch):
    monkeypatch.setattr(
        "dashboard.analyst_workspace.authorize_investigation",
        lambda payload, write=False: (False, "authentication_required"),
    )

    response = make_app().test_client().get("/workspace/analyst/CASE-1")

    assert response.status_code == 401
    assert b"Investigation not found" in response.data


def test_workspace_denies_tenant_mismatch_without_rendering_report(monkeypatch):
    captured = {}

    def deny(payload, write=False):
        captured["payload"] = payload
        return False, "investigation_not_found"

    monkeypatch.setattr("dashboard.analyst_workspace.authorize_investigation", deny)

    response = make_app().test_client().get("/workspace/analyst/CASE-1")

    assert response.status_code == 403
    assert captured["payload"]["metadata"]["tenant_id"] == "tenant-a"
    assert b"Evidence-backed report" not in response.data


def test_workspace_renders_only_after_authorization(monkeypatch):
    monkeypatch.setattr(
        "dashboard.analyst_workspace.authorize_investigation",
        lambda payload, write=False: (True, ""),
    )

    response = make_app().test_client().get("/workspace/analyst/CASE-1")

    assert response.status_code == 200
