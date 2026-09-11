import re

import pytest

from app import create_app
from services.auth.mfa import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    provisioning_uri,
    totp_code,
    verify_totp,
)
from services.auth.providers import TestEmailProvider, TestSMSProvider
from tests.credential_helpers import random_password, random_secret


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "mfa.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    application = create_app()
    application.config.update(TESTING=True, EMAIL_PROVIDER=TestEmailProvider(), SMS_PROVIDER=TestSMSProvider())
    return application


def csrf(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def login(app, client, username, password):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf(client)},
    )


def test_totp_vector_and_encryption_are_standard_and_secret_is_not_plaintext():
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert totp_code(secret, 59) == "287082"
    assert verify_totp(secret, "287082", 59)
    assert not verify_totp(secret, "287082", 59 + 120)
    app_secret = random_secret()
    envelope = encrypt_totp_secret(secret, app_secret)
    assert secret not in envelope
    assert decrypt_totp_secret(envelope, app_secret) == secret
    assert "otpauth://totp/" in provisioning_uri(secret, account_name="analyst@example.test")


def test_mfa_enrollment_requires_code_and_mfa_pending_session_is_denied(app):
    auth = app.container.require("auth_service")
    password = random_password()
    user = auth.register("mfa-analyst", "mfa@example.test", password)
    assert user.role == "analyst" and user.public()["role_label"] == "SOC-L1 Analyst"
    client = app.test_client()
    assert login(app, client, user.email, password).status_code == 200
    token = csrf(client)
    started = client.post("/api/auth/mfa/setup/start", json={}, headers={"X-CSRF-Token": token})
    assert started.status_code == 200
    uri = started.get_json()["provisioning_uri"]
    secret = re.search(r"[?&]secret=([^&]+)", uri).group(1)
    bad = client.post("/api/auth/mfa/setup/verify", json={"code": "000000"}, headers={"X-CSRF-Token": token})
    assert bad.status_code == 401
    code = totp_code(secret)
    enabled = client.post("/api/auth/mfa/setup/verify", json={"code": code}, headers={"X-CSRF-Token": token})
    assert enabled.status_code == 200
    recovery_codes = enabled.get_json()["recovery_codes"]
    assert len(recovery_codes) == 10
    assert all(code not in str(row["code_hash"]) for code in recovery_codes for row in auth.db.connect().execute("SELECT code_hash FROM auth_mfa_recovery_codes").fetchall())
    assert client.get("/profile").status_code == 401

    logged_in = login(app, client, user.email, password)
    assert logged_in.status_code == 200 and logged_in.get_json()["mfa_required"] is True
    assert client.get("/").status_code == 401
    assert client.get("/api/auth/sessions").status_code == 401
    valid = client.post("/api/auth/mfa/verify", json={"code": totp_code(secret)}, headers={"X-CSRF-Token": csrf(client)})
    assert valid.status_code == 200
    assert client.get("/profile").status_code == 200


def test_recovery_code_is_one_time_and_disable_requires_password_and_factor(app):
    auth = app.container.require("auth_service")
    password = random_password()
    user = auth.register("mfa-recovery", "mfa-recovery@example.test", password)
    client = app.test_client()
    assert login(app, client, user.email, password).status_code == 200
    token = csrf(client)
    started = client.post("/api/auth/mfa/setup/start", json={}, headers={"X-CSRF-Token": token})
    secret = re.search(r"[?&]secret=([^&]+)", started.get_json()["provisioning_uri"]).group(1)
    enabled = client.post("/api/auth/mfa/setup/verify", json={"code": totp_code(secret)}, headers={"X-CSRF-Token": token})
    recovery = enabled.get_json()["recovery_codes"][0]
    assert login(app, client, user.email, password).get_json()["mfa_required"] is True
    assert client.post("/api/auth/mfa/recovery", json={"code": recovery}, headers={"X-CSRF-Token": csrf(client)}).status_code == 200
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf(client)})
    assert login(app, client, user.email, password).get_json()["mfa_required"] is True
    assert client.post("/api/auth/mfa/recovery", json={"code": recovery}, headers={"X-CSRF-Token": csrf(client)}).status_code == 401
    assert client.post("/api/auth/mfa/verify", json={"code": totp_code(secret)}, headers={"X-CSRF-Token": csrf(client)}).status_code == 200
    bad_disable = client.post("/api/auth/mfa/disable", json={"password": "wrong", "code": totp_code(secret)}, headers={"X-CSRF-Token": csrf(client)})
    assert bad_disable.status_code == 401
    disabled = client.post("/api/auth/mfa/disable", json={"password": password, "code": totp_code(secret)}, headers={"X-CSRF-Token": csrf(client)})
    assert disabled.status_code == 200
    assert auth.get_by_id(user.id).mfa_enabled is False


def test_mfa_sensitive_endpoints_do_not_accept_missing_csrf_or_client_role(app):
    auth = app.container.require("auth_service")
    password = random_password()
    user = auth.register("mfa-csrf", "mfa-csrf@example.test", password)
    client = app.test_client()
    assert login(app, client, user.email, password).status_code == 200
    assert client.post("/api/auth/setup/start", json={}).status_code == 404
    assert client.post("/api/auth/mfa/setup/start", json={}).status_code == 403


def test_mfa_enrollment_invalidates_persistent_sessions_and_requires_fresh_login(app):
    auth = app.container.require("auth_service")
    password = random_password()
    user = auth.register("mfa-session", "mfa-session@example.test", password)
    client = app.test_client()
    assert login(app, client, user.email, password).status_code == 200
    csrf_token = csrf(client)
    started = client.post("/api/auth/mfa/setup/start", json={}, headers={"X-CSRF-Token": csrf_token})
    secret = re.search(r"[?&]secret=([^&]+)", started.get_json()["provisioning_uri"]).group(1)

    # Establish a remembered session before the MFA transition. The transition
    # must revoke it, not silently promote or preserve it.
    with client.session_transaction() as state:
        state["mfa_enrollment_pending"] = True
        state.pop("mfa_verified", None)
    raw = "remembered-raw-token"
    sid = "remembered-session"
    auth.create_persistent_session(user, raw, "tenant-session", sid, "2999-01-01T00:00:00+00:00")
    enabled = client.post("/api/auth/mfa/setup/verify", json={"code": totp_code(secret)}, headers={"X-CSRF-Token": csrf(client)})
    assert enabled.status_code == 200
    assert enabled.get_json()["mfa_enrollment_verified"] is True
    row = auth.db.connect().execute("SELECT revoked_at FROM persistent_sessions WHERE id=?", (sid,)).fetchone()
    assert row and row["revoked_at"]
    assert auth.resolve_persistent_session(sid, raw) is None
    assert client.get("/api/auth/me").status_code == 401


def test_revoked_remember_cookie_is_cleared_and_browser_restarts_authentication(app):
    auth = app.container.require("auth_service")
    password = random_password()
    user = auth.register("revoked-browser", "revoked-browser@example.test", password)
    first = app.test_client()
    assert login(app, first, user.email, password).status_code == 200
    with first.session_transaction() as state:
        state["mfa_verified"] = True
        state["organization_id"] = user.tenant_id
    # Use the service API to exercise the same durable revocation authority
    # used by logout, MFA changes, password reset, and deactivation.
    raw = "stale-browser-token"
    sid = "stale-browser-session"
    auth.create_persistent_session(user, raw, user.tenant_id, sid, "2999-01-01T00:00:00+00:00")
    auth.revoke_persistent_session(sid)
    stale = app.test_client()
    stale.set_cookie("sentinel_remember", f"{sid}.{raw}")
    response = stale.get("/profile", headers={"Accept": "text/html"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?reason=session_revoked")
    assert any("sentinel_remember=" in value and " expires=" in value.lower() for value in response.headers.getlist("Set-Cookie"))
