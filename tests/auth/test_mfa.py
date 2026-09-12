from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
import pytest
from app import create_app
from services.auth.providers import TestEmailProvider, TestSMSProvider

from services.auth.onboarding import OnboardingState
from services.auth.totp import _code

PASSWORD = "MfaStrongPassword!42"

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "mfa.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    application = create_app(); application.config.update(TESTING=True, EMAIL_PROVIDER=TestEmailProvider(), SMS_PROVIDER=TestSMSProvider())
    return application


def csrf(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def pending_user(app, name="mfa-user", email="mfa-user@example.test"):
    return app.container.require("auth_service").register(
        name, email, PASSWORD, date_of_birth="2000-01-02",
        email_verified_at=datetime.now(timezone.utc).isoformat(),
        verification_method="email", onboarding_state=OnboardingState.MFA_ENROLLMENT_REQUIRED,
    )


def login_pending(app, user):
    client = app.test_client(); token = csrf(client)
    response = client.post("/api/auth/login", json={"username": user.username, "password": PASSWORD}, headers={"X-CSRF-Token": token})
    assert response.status_code == 200 and response.get_json()["mfa_enrollment_required"] is True
    return client


def test_totp_enrollment_is_server_gated_and_protected_access_is_denied(app):
    user = pending_user(app); client = login_pending(app, user); token = csrf(client)
    started = client.post("/api/auth/mfa/enroll", json={}, headers={"X-CSRF-Token": token})
    assert started.status_code == 201
    uri = started.get_json()["provisioning_uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    challenge = started.get_json()["challenge_id"]
    assert client.get("/api/auth/me").status_code == 401
    bad = client.post("/api/auth/mfa/enroll/verify", json={"challenge_id": challenge, "code": "000000"}, headers={"X-CSRF-Token": token})
    assert bad.status_code == 400
    success = client.post("/api/auth/mfa/enroll/verify", json={"challenge_id": challenge, "code": _code(secret, int(__import__('time').time() // 30))}, headers={"X-CSRF-Token": token})
    assert success.status_code == 200
    body = success.get_json()
    assert body["account"]["onboarding_state"] == OnboardingState.AUTHENTICATED
    assert body["account"]["mfa_enabled"] is True
    assert len(body["recovery_codes"]) == 8
    assert client.get("/api/auth/me").status_code == 200


def test_totp_login_and_single_use_recovery_code(app):
    user = pending_user(app, "mfa-recovery", "mfa-recovery@example.test"); client = login_pending(app, user); token = csrf(client)
    started = client.post("/api/auth/mfa/enroll", json={}, headers={"X-CSRF-Token": token}).get_json()
    secret = parse_qs(urlparse(started["provisioning_uri"]).query)["secret"][0]
    enrolled = client.post("/api/auth/mfa/enroll/verify", json={"challenge_id": started["challenge_id"], "code": _code(secret, int(__import__('time').time() // 30))}, headers={"X-CSRF-Token": token}).get_json()
    recovery = enrolled["recovery_codes"][0]
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf(client)})
    login = client.post("/api/auth/login", json={"username": user.username, "password": PASSWORD}, headers={"X-CSRF-Token": csrf(client)})
    assert login.status_code == 200 and login.get_json()["status"] == "mfa_required"
    assert client.post("/api/auth/mfa/verify", json={"recovery_code": recovery}, headers={"X-CSRF-Token": csrf(client)}).status_code == 200
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf(client)})
    assert client.post("/api/auth/login", json={"username": user.username, "password": PASSWORD}, headers={"X-CSRF-Token": csrf(client)}).status_code == 200
    reused = client.post("/api/auth/mfa/verify", json={"recovery_code": recovery}, headers={"X-CSRF-Token": csrf(client)})
    assert reused.status_code == 401


def test_mfa_endpoints_require_strict_csrf(app):
    user = pending_user(app, "mfa-csrf", "mfa-csrf@example.test"); client = login_pending(app, user)
    assert client.post("/api/auth/mfa/enroll", json={}).status_code == 403


def test_enrollment_challenge_is_bound_to_user_and_expires(app):
    first = pending_user(app, "mfa-first", "mfa-first@example.test"); client = login_pending(app, first); token = csrf(client)
    started = client.post("/api/auth/mfa/enroll", json={}, headers={"X-CSRF-Token": token}).get_json()
    second = pending_user(app, "mfa-second", "mfa-second@example.test")
    second_client = login_pending(app, second); second_token = csrf(second_client)
    assert second_client.post("/api/auth/mfa/enroll/verify", json={"challenge_id": started["challenge_id"], "code": "123456"}, headers={"X-CSRF-Token": second_token}).status_code == 400
    with app.container.require("auth_service").db.session() as connection:
        connection.execute("UPDATE mfa_enrollment_challenges SET expires_at=? WHERE id=?", ("2000-01-01T00:00:00+00:00", started["challenge_id"]))
    assert client.post("/api/auth/mfa/enroll/verify", json={"challenge_id": started["challenge_id"], "code": "123456"}, headers={"X-CSRF-Token": token}).status_code == 400
    assert app.container.require("auth_service").get_by_id(second.id).mfa_enabled is False


def test_mfa_rate_limit_and_audit_do_not_expose_secrets(app):
    user = pending_user(app, "mfa-audit", "mfa-audit@example.test"); client = login_pending(app, user); token = csrf(client)
    started = client.post("/api/auth/mfa/enroll", json={}, headers={"X-CSRF-Token": token}).get_json()
    for _ in range(11):
        response = client.post("/api/auth/mfa/enroll/verify", json={"challenge_id": started["challenge_id"], "code": "000000"}, headers={"X-CSRF-Token": token})
    assert response.status_code == 429
    with app.container.require("auth_service").db.session() as connection:
        challenge = connection.execute("SELECT secret_ciphertext FROM mfa_enrollment_challenges WHERE id=?", (started["challenge_id"],)).fetchone()
        events = connection.execute("SELECT event_type, method, reason FROM auth_events WHERE user_id=?", (user.id,)).fetchall()
    assert challenge["secret_ciphertext"] != parse_qs(urlparse(started["provisioning_uri"]).query)["secret"][0]
    assert all("000000" not in str(row["reason"]) for row in events)
    assert any(row["event_type"] == "mfa_enrollment_failed" for row in events)
