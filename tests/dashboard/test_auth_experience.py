import pytest

import dashboard.app as dashboard_app
from database.connection import DatabaseConnection
from services.auth.auth_service import AuthService


class AuditStub:
    def record(self, *args, **kwargs):
        return None


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    registry = dashboard_app.app.container
    original_auth = registry.get("auth_service")
    original_audit = registry.get("audit_service")
    registry.register("auth_service", AuthService(DatabaseConnection(tmp_path / "auth.db")))
    registry.register("audit_service", AuditStub())
    monkeypatch.setattr(dashboard_app, "dashboard_payload", lambda: {
        "stats": {}, "cases": [], "evidence": [], "timeline": [], "iocs": [], "actions": [], "notes": []
    })
    dashboard_app.app.config["TESTING"] = True
    try:
        with dashboard_app.app.test_client() as client:
            yield client
    finally:
        registry.register("auth_service", original_auth)
        registry.register("audit_service", original_audit)


def register_user(client):
    response = client.post("/api/auth/register", json={
        "username": "analyst-browser",
        "email": "analyst-browser@example.test",
        "password": "StrongBrowserPassword123!",
        "role": "analyst",
    })
    assert response.status_code == 201


def login_user(client):
    register_user(client)
    response = client.post("/api/auth/login", json={
        "username": "analyst-browser",
        "password": "StrongBrowserPassword123!",
    })
    assert response.status_code == 200
    return response


def test_login_page_is_available(auth_client):
    response = auth_client.get("/login")

    assert response.status_code == 200
    assert b"Sign in to the SOC Command Center" in response.data
    assert b"/api/auth/login" in response.data


def test_successful_login_persists_session_and_redirects_authenticated_user(auth_client):
    login_user(auth_client)

    with auth_client.session_transaction() as session:
        assert session["user_id"]
        assert session["csrf_token"]

    assert auth_client.get("/api/auth/me").status_code == 200
    assert auth_client.get("/").status_code == 200
    assert auth_client.get("/login").status_code == 302
    assert auth_client.get("/login").headers["Location"].endswith("/")


def test_failed_login_does_not_create_authenticated_session(auth_client):
    register_user(auth_client)

    response = auth_client.post("/api/auth/login", json={
        "username": "analyst-browser",
        "password": "wrong-password",
    })

    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid_credentials"}
    assert auth_client.get("/").status_code == 401


def test_logout_clears_session_with_csrf_protection(auth_client):
    login_user(auth_client)
    with auth_client.session_transaction() as session:
        csrf = session["csrf_token"]

    response = auth_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    assert response.status_code == 200
    assert auth_client.get("/api/auth/me").status_code == 401
    assert auth_client.get("/").status_code == 401


def test_logout_without_csrf_is_rejected(auth_client):
    login_user(auth_client)

    response = auth_client.post("/api/auth/logout")

    assert response.status_code == 403
    assert auth_client.get("/api/auth/me").status_code == 200
