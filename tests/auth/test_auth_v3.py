import os
from datetime import date, timedelta
import pytest

import dashboard.app as dashboard_app
from database.connection import DatabaseConnection, database
from database.migration_runner import MigrationRunner
from services.auth.auth_service import AuthService
from services.auth.mfa import MFAService
from services.identity.canonical_authority import CanonicalAuthorityService
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
    db_path = tmp_path / "auth-v3.sqlite"
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)
    application = dashboard_app.app
    registry = application.container
    keys = ("auth_service", "canonical_authority", "mfa_service")
    previous = {key: registry.get(key) for key in keys}
    old_path = database.database_path
    old_config = {key: application.config.get(key) for key in ("TESTING", "PILOT_ACCESS_REQUIRED", "EMAIL_PROVIDER", "SMS_PROVIDER")}
    db = DatabaseConnection(db_path)
    MigrationRunner(db).run()
    auth = AuthService(db)
    registry.register("auth_service", auth)
    registry.register("canonical_authority", CanonicalAuthorityService(db, auth=auth))
    registry.register("mfa_service", MFAService(db, secret_key_provider=lambda: application.secret_key))
    application.config.update(TESTING=True, PILOT_ACCESS_REQUIRED=False, EMAIL_PROVIDER=TestEmailProvider(), SMS_PROVIDER=TestSMSProvider())
    try:
        yield application
    finally:
        for key, value in previous.items(): registry.register(key, value)
        application.config.update(old_config)
        database.database_path = old_path

def verified_registration_inputs(app, client, *, username, email, password=PASSWORD, extra=None):
    csrf = token(client)
    sent = client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    assert sent.status_code == 202 and sent.get_json().get("challenge_id")
    challenge_id = sent.get_json()["challenge_id"]
    code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    checked = client.post("/api/auth/email/verify-registration-code", json={"challenge_id": challenge_id, "email": email, "code": code}, headers={"X-CSRF-Token": csrf})
    assert checked.status_code == 200 and checked.get_json() == {"verified": True}
    payload = {"username": username, "email": email, "password": password, "date_of_birth": "2000-01-02", "email_challenge_id": challenge_id, **(extra or {})}
    return payload, csrf

def verified_register(app, client, *, username, email, password=PASSWORD, extra=None):
    payload, csrf = verified_registration_inputs(
        app, client, username=username, email=email, password=password, extra=extra
    )
    return client.post("/api/auth/register", json=payload, headers={"X-CSRF-Token": csrf})

def _registration_row_counts(db, email, username):
    with db.session() as connection:
        return {
            "users": connection.execute("SELECT COUNT(*) FROM users WHERE email=?", (email,)).fetchone()[0],
            "auth_identities": connection.execute(
                "SELECT COUNT(*) FROM auth_identities ai JOIN users u ON u.id=ai.user_id WHERE u.email=?",
                (email,),
            ).fetchone()[0],
            "canonical_identities": connection.execute(
                "SELECT COUNT(*) FROM canonical_identities WHERE email=?", (email,)
            ).fetchone()[0],
            "canonical_tenants": connection.execute(
                "SELECT COUNT(*) FROM canonical_tenants WHERE name=?", (f"{username} workspace",)
            ).fetchone()[0],
            "canonical_memberships": connection.execute(
                """SELECT COUNT(*) FROM canonical_memberships m
                   JOIN canonical_identities i ON i.actor_id=m.actor_id
                   WHERE i.email=?""",
                (email,),
            ).fetchone()[0],
        }

def _assert_failed_registration_is_retryable(app, monkeypatch, *, username, email, fail_at):
    client = app.test_client()
    payload, csrf = verified_registration_inputs(
        app, client, username=username, email=email
    )
    authority = app.container.require("canonical_authority")
    original = getattr(authority.tenants if fail_at == "tenant" else authority.memberships, "create" if fail_at == "tenant" else "add")
    injected_failure = []

    if fail_at == "tenant":
        def fail_tenant_creation(*args, **kwargs):
            injected_failure.append("tenant")
            raise RuntimeError("injected tenant creation failure")

        monkeypatch.setattr(authority.tenants, "create", fail_tenant_creation)
    else:
        def fail_after_membership_insert(*args, **kwargs):
            original(*args, **kwargs)
            injected_failure.append("membership")
            raise RuntimeError("injected membership creation failure")

        monkeypatch.setattr(authority.memberships, "add", fail_after_membership_insert)

    failed = client.post("/api/auth/register", json=payload, headers={"X-CSRF-Token": csrf})
    assert failed.status_code == 500
    assert injected_failure == [fail_at]
    assert _registration_row_counts(app.container.require("auth_service").db, email, username) == {
        "users": 0,
        "auth_identities": 0,
        "canonical_identities": 0,
        "canonical_tenants": 0,
        "canonical_memberships": 0,
    }

    monkeypatch.setattr(authority.tenants if fail_at == "tenant" else authority.memberships,
                        "create" if fail_at == "tenant" else "add", original)
    retried = client.post("/api/auth/register", json=payload, headers={"X-CSRF-Token": csrf})
    assert retried.status_code == 201, retried.get_json()
    assert _registration_row_counts(app.container.require("auth_service").db, email, username) == {
        "users": 1,
        "auth_identities": 1,
        "canonical_identities": 1,
        "canonical_tenants": 1,
        "canonical_memberships": 1,
    }

def test_registration_rolls_back_identity_when_tenant_creation_fails(app, monkeypatch):
    _assert_failed_registration_is_retryable(
        app,
        monkeypatch,
        username="tenant-failure-user",
        email="tenant-failure@example.test",
        fail_at="tenant",
    )

def test_registration_rolls_back_tenant_and_membership_when_membership_creation_fails(app, monkeypatch):
    _assert_failed_registration_is_retryable(
        app,
        monkeypatch,
        username="membership-failure-user",
        email="membership-failure@example.test",
        fail_at="membership",
    )

def test_registration_fails_closed_when_canonical_authority_uses_separate_database(app, tmp_path):
    client = app.test_client()
    email = "separate-authority@example.test"
    payload, csrf = verified_registration_inputs(
        app, client, username="separate-authority-user", email=email
    )
    separate_db = DatabaseConnection(tmp_path / "separate-canonical-authority.sqlite")
    MigrationRunner(separate_db).run()
    app.container.register("canonical_authority", CanonicalAuthorityService(separate_db))

    response = client.post("/api/auth/register", json=payload, headers={"X-CSRF-Token": csrf})

    assert response.status_code == 500
    assert _registration_row_counts(app.container.require("auth_service").db, email, "separate-authority-user") == {
        "users": 0,
        "auth_identities": 0,
        "canonical_identities": 0,
        "canonical_tenants": 0,
        "canonical_memberships": 0,
    }
    with separate_db.session() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM canonical_identities WHERE email=?", (email,)
        ).fetchone()[0] == 0

def token(client): return client.get("/api/auth/csrf").get_json()["csrf_token"]

def test_v3_signup_email_only_and_analyst_binding(app):
    client = app.test_client()
    created = verified_register(app, client, username="v3-analyst", email="v3@example.test", extra={"role":"admin", "tenant_id":"attacker"})
    assert created.status_code == 201 and created.get_json()["role"] == "analyst"
    assert created.get_json().get("phone_number") is None

def test_v3_optional_phone_must_be_verified_before_storage(app):
    client = app.test_client(); csrf = token(client)
    email = "v3-phone@example.test"
    sent_email = client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    email_challenge = sent_email.get_json()["challenge_id"]
    email_code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/email/verify-registration-code", json={"challenge_id": email_challenge, "email": email, "code": email_code}, headers={"X-CSRF-Token": csrf}).status_code == 200
    send = client.post("/api/auth/phone/send-code", json={"country": "NG", "phone": "08031234567"}, headers={"X-CSRF-Token": csrf})
    assert send.status_code == 202
    challenge = send.get_json()["challenge_id"]
    code = app.config["SMS_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/phone/verify-code", json={"challenge_id": challenge, "code": code}, headers={"X-CSRF-Token": csrf}).status_code == 200
    created = client.post("/api/auth/register", json={"username":"v3-phone","email":email,"password":PASSWORD,"country":"NG","phone":"08031234567","phone_challenge_id":challenge,"email_challenge_id":email_challenge,"date_of_birth":"2000-01-02"}, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201
    user = app.container.require("auth_service").get_by_email(email)
    assert user.phone_number == "+2348031234567" and user.phone_verified_at

def test_v3_csrf_and_dob_rejection(app):
    client = app.test_client()
    assert client.post("/api/auth/register", data={}).status_code == 403
    csrf = token(client)
    for dob in (date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat(), "2024-02-30"):
        email = f"dob-{len(dob)}-{dob.replace('-', '')}@example.test"
        sent = client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
        challenge = sent.get_json()["challenge_id"]
        code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
        assert client.post("/api/auth/email/verify-registration-code", json={"email": email, "challenge_id": challenge, "code": code}, headers={"X-CSRF-Token": csrf}).status_code == 200
        response = client.post("/api/auth/register", json={"username":"underage-user", "email":email, "password":PASSWORD, "date_of_birth":dob, "email_challenge_id":challenge}, headers={"X-CSRF-Token":csrf})
        assert response.status_code == 400

def test_v3_email_otp_is_generic_and_single_use(app):
    client = app.test_client(); csrf = token(client)
    assert client.post("/api/auth/email/send-code", json={"email":"unknown@example.test"}, headers={"X-CSRF-Token":csrf}).status_code == 202

def test_v3_email_otp_authentication_and_replay_protection(app):
    client = app.test_client(); assert verified_register(app, client, username="email-user", email="email-user@example.test").status_code == 201
    csrf = token(client); response = client.post("/api/auth/email/send-code", json={"email":"email-user@example.test"}, headers={"X-CSRF-Token":csrf})
    assert response.status_code == 202
    challenge = app.container.require("auth_service").db.connect().execute("SELECT id FROM otp_challenges ORDER BY created_at DESC LIMIT 1").fetchone()["id"]
    code = app.config["EMAIL_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/email/verify-code", json={"challenge_id":challenge,"code":code}, headers={"X-CSRF-Token":csrf}).status_code == 200
    replay_csrf = token(client)
    assert client.post("/api/auth/email/verify-code", json={"challenge_id":challenge,"code":code}, headers={"X-CSRF-Token":replay_csrf}).status_code == 400

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
    assert verified_register(app, client, username="recovery-user", email="recovery@example.test").status_code == 201
    assert client.post("/api/auth/login", json={"username":"recovery@example.test","password":PASSWORD,"remember_me":True}, headers={"X-CSRF-Token":csrf}).status_code == 200
    csrf = token(client)
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
    assert verified_register(app, client, username="cookie-user", email="cookie@example.test").status_code == 201
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
    assert verified_register(app, client, username="rotation-user", email="rotation@example.test").status_code == 201
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
