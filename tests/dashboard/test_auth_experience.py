import pytest
from tests.credential_helpers import random_password
from datetime import datetime, timedelta, timezone

import dashboard.app as dashboard_app
from database.connection import DatabaseConnection
from database.migration_runner import MigrationRunner
from database.connection import database
from services.auth.auth_service import AuthService
from services.auth.providers import TestEmailProvider


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
    original_email_provider = dashboard_app.app.config.get("EMAIL_PROVIDER")
    original_legacy_compat = dashboard_app.app.config.get("AUTH_LEGACY_JSON_COMPAT")
    original_testing = dashboard_app.app.config.get("TESTING")
    original_pilot_required = dashboard_app.app.config.get("PILOT_ACCESS_REQUIRED")
    auth_path = tmp_path / "auth.db"
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(auth_path))
    monkeypatch.setattr(dashboard_app, "DB_PATH", auth_path)
    original_database_path = database.database_path
    database.database_path = str(auth_path)
    auth_db = DatabaseConnection(auth_path)
    MigrationRunner(auth_db).run()
    registry.register("auth_service", AuthService(auth_db))
    registry.register("audit_service", AuditStub())
    monkeypatch.setattr(dashboard_app, "dashboard_payload", lambda: {
        "stats": {}, "cases": [], "evidence": [], "timeline": [], "iocs": [], "actions": [], "notes": []
    })
    dashboard_app.app.config["TESTING"] = True
    dashboard_app.app.config["PILOT_ACCESS_REQUIRED"] = False
    email_provider = TestEmailProvider()
    dashboard_app.app.config["EMAIL_PROVIDER"] = email_provider
    try:
        with dashboard_app.app.test_client() as client:
            yield client
    finally:
        registry.register("auth_service", original_auth)
        registry.register("audit_service", original_audit)
        dashboard_app.app.config["EMAIL_PROVIDER"] = original_email_provider
        if original_legacy_compat is None:
            dashboard_app.app.config.pop("AUTH_LEGACY_JSON_COMPAT", None)
        else:
            dashboard_app.app.config["AUTH_LEGACY_JSON_COMPAT"] = original_legacy_compat
        if original_testing is None:
            dashboard_app.app.config.pop("TESTING", None)
        else:
            dashboard_app.app.config["TESTING"] = original_testing
        if original_pilot_required is None:
            dashboard_app.app.config.pop("PILOT_ACCESS_REQUIRED", None)
        else:
            dashboard_app.app.config["PILOT_ACCESS_REQUIRED"] = original_pilot_required
        database.database_path = original_database_path


def csrf_token(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def register_user(client, *, username="analyst-browser", email="analyst-browser@example.test", password=BROWSER_PASSWORD, extra=None):
    csrf = csrf_token(client)
    sent = client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    assert sent.status_code == 202 and sent.get_json().get("challenge_id")
    challenge_id = sent.get_json()["challenge_id"]
    code = dashboard_app.app.config["EMAIL_PROVIDER"].messages[-1]["code"]

    wrong_code = f"{(int(code) + 1) % 1_000_000:06d}"
    invalid = client.post("/api/auth/email/verify-registration-code", json={"email": email, "challenge_id": challenge_id, "code": wrong_code}, headers={"X-CSRF-Token": csrf})
    assert invalid.status_code == 400
    verified = client.post("/api/auth/email/verify-registration-code", json={"email": email, "challenge_id": challenge_id, "code": code}, headers={"X-CSRF-Token": csrf})
    assert verified.status_code == 200 and verified.get_json() == {"verified": True}
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "date_of_birth": "1990-01-01",
        "email_challenge_id": challenge_id,
        **(extra or {}),
    }
    return client.post("/api/auth/register", json=payload, headers={"X-CSRF-Token": csrf})


def login_user(client):
    created = register_user(client)
    assert created.status_code == 201
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
    assert b"/api/auth/mfa/enroll" in response.data
    assert b"/api/auth/mfa/verify" in response.data
    assert b"mfa-panel" in response.data


def test_signup_page_is_available_without_role_or_tenant_controls(auth_client):
    response = auth_client.get("/signup")

    assert response.status_code == 200
    assert b"Create your analyst account" in response.data
    assert b"id=\"confirm\"" in response.data
    assert b"Recovery phone (optional)" in response.data
    assert b"Verify this email address" in response.data
    assert b"name=\"role\"" not in response.data
    assert b"name=\"tenant_id\"" not in response.data


def test_signup_creates_analyst_user_and_duplicate_is_rejected(auth_client):
    payload = {
        "username": "new-analyst",
        "email": "new-analyst@example.test",
        "password": SIGNUP_PASSWORD,
    }

    created = register_user(auth_client, username=payload["username"], email=payload["email"], password=payload["password"], extra={"role": "admin", "tenant_id": "attacker", "workspace_id": "attacker"})
    service = dashboard_app.app.container.require("auth_service")
    with service.db.session() as connection:
        connection.execute("UPDATE otp_challenges SET created_at=? WHERE destination=? AND purpose='registration_email'", ((datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat(), payload["email"]))
    duplicate = register_user(auth_client, username="duplicate-identifier", email=payload["email"], password=payload["password"])
    elevated = register_user(auth_client, username="another-analyst", email="another@example.test", password=SIGNUP_PASSWORD, extra={"role": "admin", "tenant_id": "attacker"})

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert elevated.status_code == 201
    assert created.get_json()["role"] == "analyst"
    assert elevated.get_json()["role"] == "analyst"
    created_user = service.get_by_email(payload["email"])
    assert created_user and created_user.password_hash != payload["password"]
    assert created_user.tenant_id != "attacker"
    memberships = dashboard_app.app.container.require("canonical_authority").memberships.list_for_actor(created_user.actor_id)
    assert len(memberships) == 1 and memberships[0].role == "analyst"
    with service.db.session() as connection:
        events = connection.execute("SELECT event_type,method,outcome,reason FROM auth_events").fetchall()
    audit_text = repr([tuple(row) for row in events])
    assert payload["password"] not in audit_text
    assert dashboard_app.app.config["EMAIL_PROVIDER"].messages[0]["code"] not in audit_text


def test_public_json_registration_cannot_use_legacy_verification_bypass(auth_client):
    dashboard_app.app.config["AUTH_LEGACY_JSON_COMPAT"] = True
    response = auth_client.post("/api/auth/register", json={
        "username": "unverified-user", "email": "unverified@example.test",
        "password": SIGNUP_PASSWORD, "date_of_birth": "1990-01-01",
    })
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_registration"}
    assert dashboard_app.app.container.require("auth_service").get_by_email("unverified@example.test") is None


def test_public_registration_cannot_adopt_an_existing_canonical_identity(auth_client):
    email = "existing-canonical@example.test"
    authority = dashboard_app.app.container.require("canonical_authority")
    tenant = authority.tenants.create("Existing tenant", "existing-canonical-tenant")
    identity = authority.identities.create(email, actor_id="existing-canonical-actor")
    authority.memberships.add(tenant.tenant_id, identity.actor_id, "soc_manager")
    response = register_user(auth_client, username="identity-collision", email=email)
    assert response.status_code == 409
    assert response.get_json() == {"error": "registration_unavailable"}
    assert dashboard_app.app.container.require("auth_service").get_by_email(email) is None


def test_browser_registration_keeps_csrf_enforcement(auth_client):
    response = auth_client.post("/api/auth/register", json={
        "username": "csrf-user", "email": "csrf@example.test", "password": SIGNUP_PASSWORD,
        "date_of_birth": "1990-01-01",
    }, headers={"Origin": "https://attacker.example"})
    assert response.status_code == 403
    assert response.get_json() == {"error": "csrf_validation_failed"}


def test_email_challenge_is_session_bound_and_replay_is_rejected(auth_client):
    csrf = csrf_token(auth_client)
    sent = auth_client.post("/api/auth/email/send-registration-code", json={"email": "session-bound@example.test"}, headers={"X-CSRF-Token": csrf})
    challenge_id = sent.get_json()["challenge_id"]
    code = dashboard_app.app.config["EMAIL_PROVIDER"].messages[-1]["code"]

    other_client = dashboard_app.app.test_client()
    other_csrf = csrf_token(other_client)
    cross_session = other_client.post("/api/auth/email/verify-registration-code", json={"email": "session-bound@example.test", "challenge_id": challenge_id, "code": code}, headers={"X-CSRF-Token": other_csrf})
    assert cross_session.status_code == 400

    verified = auth_client.post("/api/auth/email/verify-registration-code", json={"email": "session-bound@example.test", "challenge_id": challenge_id, "code": code}, headers={"X-CSRF-Token": csrf})
    assert verified.status_code == 200 and verified.get_json()["verified"] is True
    replay = auth_client.post("/api/auth/email/verify-registration-code", json={"email": "session-bound@example.test", "challenge_id": challenge_id, "code": code}, headers={"X-CSRF-Token": csrf})
    assert replay.status_code == 400
    wrong_email = auth_client.post("/api/auth/register", json={
        "username": "wrong-email-user", "email": "different@example.test", "password": SIGNUP_PASSWORD,
        "date_of_birth": "1990-01-01", "email_challenge_id": challenge_id,
    }, headers={"X-CSRF-Token": csrf})
    assert wrong_email.status_code == 400


def test_consumed_email_challenge_that_expires_before_registration_is_rejected(auth_client):
    csrf = csrf_token(auth_client)
    email = "expired-at-registration@example.test"
    sent = auth_client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    challenge_id = sent.get_json()["challenge_id"]
    code = dashboard_app.app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    assert auth_client.post("/api/auth/email/verify-registration-code", json={"email": email, "challenge_id": challenge_id, "code": code}, headers={"X-CSRF-Token": csrf}).status_code == 200
    service = dashboard_app.app.container.require("auth_service")
    with service.db.session() as connection:
        connection.execute("UPDATE otp_challenges SET expires_at=? WHERE id=?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), challenge_id))
    response = auth_client.post("/api/auth/register", json={"username": "expired-user", "email": email, "password": SIGNUP_PASSWORD, "date_of_birth": "1990-01-01", "email_challenge_id": challenge_id}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 400
    assert service.get_by_email(email) is None


def test_expired_email_code_cannot_be_verified_or_registered(auth_client):
    csrf = csrf_token(auth_client)
    email = "expired-before-verification@example.test"
    sent = auth_client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    challenge_id = sent.get_json()["challenge_id"]
    code = dashboard_app.app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    service = dashboard_app.app.container.require("auth_service")
    with service.db.session() as connection:
        connection.execute("UPDATE otp_challenges SET expires_at=? WHERE id=?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), challenge_id))
    verify = auth_client.post("/api/auth/email/verify-registration-code", json={"email": email, "challenge_id": challenge_id, "code": code}, headers={"X-CSRF-Token": csrf})
    assert verify.status_code == 400
    register = auth_client.post("/api/auth/register", json={"username": "expired-before-user", "email": email, "password": SIGNUP_PASSWORD, "date_of_birth": "1990-01-01", "email_challenge_id": challenge_id}, headers={"X-CSRF-Token": csrf})
    assert register.status_code == 400
    assert service.get_by_email(email) is None


def test_login_works_after_signup_and_dashboard_stays_protected(auth_client):
    payload = {
        "username": "signup-login-analyst",
        "email": "signup-login@example.test",
        "password": SIGNUP_PASSWORD,
    }

    assert auth_client.get("/").status_code == 401
    assert register_user(auth_client, username=payload["username"], email=payload["email"], password=payload["password"]).status_code == 201
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
