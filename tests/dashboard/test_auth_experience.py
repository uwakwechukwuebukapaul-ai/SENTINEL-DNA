import pytest
from tests.credential_helpers import random_password

import dashboard.app as dashboard_app
from database.connection import DatabaseConnection
from database.connection import database
from services.auth.auth_service import AuthService


BROWSER_PASSWORD = random_password()
SIGNUP_PASSWORD = random_password()


class AuditStub:
    def record(self, *args, **kwargs):
        return None


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    registry = dashboard_app.app.container
    original_auth = registry.get("auth_service")
    original_audit = registry.get("audit_service")
    auth_path = tmp_path / "auth.db"
    original_database_path = database.database_path
    database.database_path = str(auth_path)
    registry.register("auth_service", AuthService(DatabaseConnection(auth_path)))
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
        database.database_path = original_database_path


def register_user(client):
    response = client.post("/api/auth/register", json={
        "username": "analyst-browser",
        "email": "analyst-browser@example.test",
        "password": BROWSER_PASSWORD,
        "role": "analyst",
    })
    assert response.status_code == 201


def login_user(client):
    register_user(client)
    response = client.post("/api/auth/login", json={
        "username": "analyst-browser",
        "password": BROWSER_PASSWORD,
    })
    assert response.status_code == 200
    return response


def test_login_page_is_available(auth_client):
    response = auth_client.get("/login")

    assert response.status_code == 200
    assert b"Sign in to the SOC Command Center" in response.data
    assert b"/api/auth/login" in response.data


def test_signup_page_is_available_without_role_or_tenant_controls(auth_client):
    response = auth_client.get("/signup")

    assert response.status_code == 200
    assert b"Create your analyst account" in response.data
    assert b"id=\"confirm\"" in response.data
    assert b"name=\"role\"" not in response.data
    assert b"name=\"tenant_id\"" not in response.data


def test_signup_creates_analyst_user_and_duplicate_is_rejected(auth_client):
    payload = {
        "username": "new-analyst",
        "email": "new-analyst@example.test",
        "password": SIGNUP_PASSWORD,
    }

    created = auth_client.post("/api/auth/register", json=payload)
    duplicate = auth_client.post("/api/auth/register", json=payload)
    elevated = auth_client.post("/api/auth/register", json={**payload, "username": "another-analyst", "email": "another@example.test", "role": "admin"})

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert elevated.status_code == 201
    assert created.get_json()["role"] == "analyst"
    assert elevated.get_json()["role"] == "analyst"


def test_login_works_after_signup_and_dashboard_stays_protected(auth_client):
    payload = {
        "username": "signup-login-analyst",
        "email": "signup-login@example.test",
        "password": SIGNUP_PASSWORD,
    }

    assert auth_client.get("/").status_code == 401
    assert auth_client.post("/api/auth/register", json=payload).status_code == 201
    assert auth_client.post("/api/auth/login", json={"username": payload["username"], "password": payload["password"]}).status_code == 200
    assert auth_client.get("/").status_code == 200


def test_successful_login_persists_session_and_redirects_authenticated_user(auth_client):
    login_user(auth_client)

    with auth_client.session_transaction() as session:
        assert session["user_id"]
        assert session["csrf_token"]

    assert auth_client.get("/api/auth/me").status_code == 200
    assert auth_client.get("/").status_code == 200
    assert auth_client.get("/login").status_code == 302
    assert auth_client.get("/login").headers["Location"].endswith("/")


def test_authenticated_dashboard_renders_analyst_onboarding_and_navigation(auth_client):
    login_user(auth_client)
    with auth_client.session_transaction() as session:
        tenant_id = session["organization_id"]

    response = auth_client.get("/")

    assert response.status_code == 200
    assert b"Welcome to Sentinel DNA SOC Command Center" in response.data
    assert b"First-run analyst guide" in response.data
    assert b"Investigations" in response.data
    assert b"Threat Intelligence" in response.data
    assert b"Evidence Analysis" in response.data
    assert b"AI Investigator" in response.data
    assert b"Command Center" in response.data
    assert b"Analyst Profile" in response.data
    assert b"Logout" in response.data
    assert b"analyst-browser" in response.data
    assert b"analyst-browser@example.test" in response.data
    assert b"Analyst" in response.data
    assert tenant_id.encode() in response.data


def test_analyst_profile_is_authenticated_and_uses_server_identity(auth_client):
    login_user(auth_client)
    with auth_client.session_transaction() as session:
        tenant_id = session["organization_id"]

    response = auth_client.get("/profile")

    assert response.status_code == 200
    assert b"Analyst profile" in response.data
    assert b"analyst-browser@example.test" in response.data
    assert tenant_id.encode() in response.data


def test_dashboard_and_profile_remain_protected_without_login(auth_client):
    assert auth_client.get("/").status_code == 401
    assert auth_client.get("/profile").status_code == 401


def test_failed_login_does_not_create_authenticated_session(auth_client):
    register_user(auth_client)

    response = auth_client.post("/api/auth/login", json={
        "username": "analyst-browser",
        "password": random_password(),
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
