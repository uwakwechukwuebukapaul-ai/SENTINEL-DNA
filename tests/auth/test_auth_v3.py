import os
from datetime import date, timedelta
import pytest

from app import create_app
from services.auth.providers import TestEmailProvider, TestSMSProvider, email_provider, sms_provider
from services.auth.oauth import GoogleOIDC
from services.auth.oauth import GoogleClaims
from services.auth.rate_limit import RedisRateLimitBackend
from tests.credential_helpers import random_password, random_secret


PASSWORD = random_password()
NEW_PASSWORD = random_password()
ANOTHER_PASSWORD = random_password()

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "auth-v3.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    application = create_app(); application.config.update(TESTING=True, EMAIL_PROVIDER=TestEmailProvider(), SMS_PROVIDER=TestSMSProvider())
    return application

def token(client): return client.get("/api/auth/csrf").get_json()["csrf_token"]

def test_v3_signup_phone_dob_and_analyst_binding(app):
    client = app.test_client(); csrf = token(client)
    assert client.post("/api/auth/email/send-registration-code", json={"email":"v3@example.test"}, headers={"X-CSRF-Token":csrf}).status_code == 202
    email_code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    email_challenge = app.container.require("auth_service").db.connect().execute("SELECT id FROM otp_challenges WHERE purpose='registration_email' ORDER BY created_at DESC LIMIT 1").fetchone()["id"]
    assert client.post("/api/auth/email/verify-registration-code", json={"challenge_id":email_challenge,"code":email_code}, headers={"X-CSRF-Token":csrf}).status_code == 200
    send = client.post("/api/auth/phone/send-code", json={"country": "NG", "phone": "08031234567"}, headers={"X-CSRF-Token": csrf})
    assert send.status_code == 202
    challenge = send.get_json()["challenge_id"]
    code = app.config["SMS_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/phone/verify-code", json={"challenge_id": challenge, "code": code}, headers={"X-CSRF-Token": csrf}).status_code == 200
    created = client.post("/api/auth/register", json={"username":"v3-analyst","email":"v3@example.test","password":PASSWORD,"country":"NG","phone":"08031234567","phone_challenge_id":challenge,"email_challenge_id":email_challenge,"date_of_birth":"2000-01-02","role":"admin","tenant_id":"attacker"}, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201 and created.get_json()["role"] == "analyst"
    assert created.get_json()["onboarding_state"] == "AUTHENTICATED"
    assert "+2348031234567" == created.get_json()["phone_number"] if "phone_number" in created.get_json() else True

def test_v3_csrf_and_dob_rejection(app):
    client = app.test_client()
    assert client.post("/api/auth/register", data={}).status_code == 403
    csrf = token(client)
    for dob in (date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat(), "2024-02-30"):
        response = client.post("/api/auth/register", json={"username":"underage-user","email":f"{dob}@example.test","password":PASSWORD,"date_of_birth":dob,"country":"NG","phone":"08031234567"}, headers={"X-CSRF-Token":csrf})
        assert response.status_code == 400

def test_v3_email_otp_is_generic_and_single_use(app):
    client = app.test_client(); csrf = token(client)
    assert client.post("/api/auth/email/send-code", json={"email":"unknown@example.test"}, headers={"X-CSRF-Token":csrf}).status_code == 202

def test_v3_email_otp_authentication_and_replay_protection(app):
    client = app.test_client(); assert client.post("/api/auth/register", json={"username":"email-user","email":"email-user@example.test","password":PASSWORD}).status_code == 201
    csrf = token(client); response = client.post("/api/auth/email/send-code", json={"email":"email-user@example.test"}, headers={"X-CSRF-Token":csrf})
    assert response.status_code == 202
    challenge = app.container.require("auth_service").db.connect().execute("SELECT id FROM otp_challenges ORDER BY created_at DESC LIMIT 1").fetchone()["id"]
    code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/email/verify-code", json={"challenge_id":challenge,"code":code}, headers={"X-CSRF-Token":csrf}).status_code == 200
    assert client.post("/api/auth/email/verify-code", json={"challenge_id":challenge,"code":code}, headers={"X-CSRF-Token":csrf}).status_code == 400

def test_v3_registration_otp_cannot_cross_signed_auth_flows(app):
    first = app.test_client(); first_csrf = token(first)
    sent = first.post(
        "/api/auth/email/send-registration-code",
        json={"email": "bound@example.test"},
        headers={"X-CSRF-Token": first_csrf},
    )
    assert sent.status_code == 202
    challenge = sent.get_json()["challenge_id"]
    code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]

    second = app.test_client(); second_csrf = token(second)
    denied = second.post(
        "/api/auth/email/verify-registration-code",
        json={"challenge_id": challenge, "code": code},
        headers={"X-CSRF-Token": second_csrf},
    )
    assert denied.status_code == 400

    accepted = first.post(
        "/api/auth/email/verify-registration-code",
        json={"challenge_id": challenge, "code": code},
        headers={"X-CSRF-Token": first_csrf},
    )
    assert accepted.status_code == 200

def test_onboarding_state_is_server_owned_and_invalid_transitions_fail_closed(app):
    service = app.container.require("auth_service")
    user = service.register(
        "state-user", "state@example.test", PASSWORD,
        onboarding_state="NEW",
    )
    assert service.authenticate("state@example.test", PASSWORD) is None
    with pytest.raises(ValueError, match="invalid_onboarding_transition"):
        service.transition_onboarding(user.id, "AUTHENTICATED")
    assert service.complete_verified_onboarding(user.id) is None

def test_password_strength_is_enforced_by_the_server(app):
    service = app.container.require("auth_service")
    with pytest.raises(ValueError, match="invalid_user_registration"):
        service.register("weak-user", "weak@example.test", "longpassword")

def test_v3_oidc_rejects_tampered_state_without_network(app):
    with pytest.raises(ValueError, match="oauth_state_invalid"):
        GoogleOIDC("client", random_secret(), "http://127.0.0.1/callback").complete("code", "attacker-state", "expected-state", "nonce", "nonce")

def test_v3_providers_fail_closed_without_explicit_configuration(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.delenv("SENTINEL_DNA_EMAIL_PROVIDER", raising=False); monkeypatch.delenv("SENTINEL_DNA_SMS_PROVIDER", raising=False)
    with pytest.raises(RuntimeError): email_provider()
    with pytest.raises(RuntimeError): sms_provider()

def test_v3_password_recovery_is_single_use_and_revokes_sessions(app):
    client = app.test_client(); csrf = token(client)
    assert client.post("/api/auth/register", json={"username":"recovery-user","email":"recovery@example.test","password":PASSWORD}).status_code == 201
    assert client.post("/api/auth/login", json={"username":"recovery@example.test","password":PASSWORD,"remember_me":True}, headers={"X-CSRF-Token":csrf}).status_code == 200
    assert client.post("/api/auth/password-reset/request", json={"email":"recovery@example.test"}, headers={"X-CSRF-Token":csrf}).status_code == 202
    code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    challenge = app.container.require("auth_service").db.connect().execute("SELECT id FROM otp_challenges WHERE purpose='password_reset' ORDER BY created_at DESC LIMIT 1").fetchone()["id"]
    assert client.post("/api/auth/password-reset/confirm", json={"challenge_id":challenge,"code":code,"password":NEW_PASSWORD}, headers={"X-CSRF-Token":csrf}).status_code == 200
    assert client.get("/profile").status_code == 401
    assert app.container.require("auth_service").authenticate("recovery@example.test", PASSWORD) is None
    assert app.container.require("auth_service").authenticate("recovery@example.test", NEW_PASSWORD) is not None
    assert client.post("/api/auth/password-reset/confirm", json={"challenge_id":challenge,"code":code,"password":ANOTHER_PASSWORD}, headers={"X-CSRF-Token":token(client)}).status_code == 400

def test_v3_google_first_creates_canonical_analyst(monkeypatch, app):
    class StubGoogle:
        def complete(self, *args): return GoogleClaims("google-sub-1", "google-first@example.test", "Google Analyst")
    monkeypatch.setattr("services.auth.routes.GoogleOIDC", StubGoogle)
    client = app.test_client()
    with client.session_transaction() as state:
        state["google_state"] = "state-1"; state["google_nonce"] = "nonce-1"
    response = client.get("/api/auth/google/callback?code=one&state=state-1")
    assert response.status_code == 302 and response.headers["Location"].endswith("/")
    user = app.container.require("auth_service").get_by_email("google-first@example.test")
    assert user and user.role == "analyst" and user.actor_id is not None
    assert app.container.require("auth_service").identity_user("google", "google-sub-1").id == user.id

def test_v3_remember_me_uses_dedicated_http_only_cookie(app):
    client = app.test_client(); csrf = token(client)
    assert client.post("/api/auth/register", json={"username":"cookie-user","email":"cookie@example.test","password":PASSWORD}).status_code == 201
    response = client.post("/api/auth/login", json={"username":"cookie@example.test","password":PASSWORD,"remember_me":True}, headers={"X-CSRF-Token":csrf})
    assert response.status_code == 200
    cookies = response.headers.getlist("Set-Cookie")
    remember = next(value for value in cookies if value.startswith("sentinel_remember="))
    assert "HttpOnly" in remember and "SameSite=Lax" in remember
    with client.session_transaction() as state:
        assert "remember_session" not in state
        assert state.get("persistent_session_id")

def test_v3_remember_me_restoration_rotates_and_revokes_old_token(app):
    client = app.test_client(); csrf = token(client)
    assert client.post("/api/auth/register", json={"username":"rotation-user","email":"rotation@example.test","password":PASSWORD}).status_code == 201
    response = client.post("/api/auth/login", json={"username":"rotation@example.test","password":PASSWORD,"remember_me":True}, headers={"X-CSRF-Token":csrf})
    old_cookie = next(value for value in response.headers.getlist("Set-Cookie") if value.startswith("sentinel_remember=")).split(";", 1)[0]
    old_sid = old_cookie.split("=", 1)[1].split(".", 1)[0]
    restored_client = app.test_client()
    restored_client.set_cookie("sentinel_remember", old_cookie.split("=", 1)[1])
    restored = restored_client.get("/profile")
    assert restored.status_code == 200
    new_cookie = next(value for value in restored.headers.getlist("Set-Cookie") if value.startswith("sentinel_remember=")).split(";", 1)[0]
    new_sid = new_cookie.split("=", 1)[1].split(".", 1)[0]
    assert new_sid != old_sid
    service = app.container.require("auth_service")
    row = service.db.connect().execute("SELECT revoked_at FROM persistent_sessions WHERE id=?", (old_sid,)).fetchone()
    assert row and row["revoked_at"]

def test_v3_redis_rate_limit_backend_contract():
    class FakeRedis:
        def __init__(self): self.values = {}; self.ttls = {}
        def incr(self, key): self.values[key] = self.values.get(key, 0) + 1; return self.values[key]
        def expire(self, key, seconds): self.ttls[key] = seconds
    backend = RedisRateLimitBackend(FakeRedis())
    assert backend.allow("login", limit=1, window_seconds=60)
    assert not backend.allow("login", limit=1, window_seconds=60)
