from flask import Flask

from services.auth import permissions
from services.favp_operations.routes import create_favp_blueprint


class Container:
    def __init__(self, service=None):
        self.service = service

    def get(self, name):
        if name == "favp_operations":
            return self.service
        return None


class ScenarioService:
    def list_scenarios(self):
        return [{"scenario_id": "FAVP-SCN-001", "synthetic": True}]


def make_app(service=None):
    app = Flask(__name__)
    app.secret_key = "test-only"
    app.container = Container(service)
    app.register_blueprint(create_favp_blueprint())
    return app


def test_favp_routes_require_an_existing_role(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: None)
    response = make_app(ScenarioService()).test_client().get("/api/favp/scenarios")
    assert response.status_code == 401


def test_favp_manager_routes_reject_analyst_role(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: "analyst")
    response = make_app(ScenarioService()).test_client().post(
        "/api/favp/organizations",
        json={"organization_ref": "org", "display_name": "Organization"},
    )
    assert response.status_code == 403


def test_favp_scenario_read_uses_existing_pilot_read_permission(monkeypatch):
    monkeypatch.setattr(permissions, "current_role", lambda: "admin")
    response = make_app(ScenarioService()).test_client().get("/api/favp/scenarios")
    assert response.status_code == 200
    assert response.get_json()["scenarios"][0]["synthetic"] is True
