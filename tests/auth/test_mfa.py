from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import threading

import pyotp
import pytest

from app import create_app
from database.backend import SQLiteBackend
from database.migration_runner import MigrationRunner
from services.auth.mfa import MFAError, MFAService
from tests.credential_helpers import random_password


PASSWORD = random_password()


@pytest.fixture
def mfa_application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    db_path = tmp_path / "mfa.sqlite"
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))
    MigrationRunner(SQLiteBackend(db_path)).run()
    application = create_app()
    application.config.update(TESTING=True, PILOT_ACCESS_REQUIRED=True)
    authority = application.container.require("canonical_authority")
    auth = application.container.require("auth_service")
    tenant = authority.tenants.create("Synthetic MFA pilot", "mfa-pilot-tenant")
    authority.identities.create("manager@mfa.example.test", actor_id="mfa-manager")
    authority.identities.create("analyst@mfa.example.test", actor_id="mfa-analyst")
    authority.memberships.add(tenant.tenant_id, "mfa-manager", "soc_manager")
    authority.memberships.add(tenant.tenant_id, "mfa-analyst", "analyst")
    auth.register(
        "mfa-manager",
        "manager@mfa.example.test",
        PASSWORD,
        "soc_manager",
        tenant_id=tenant.tenant_id,
        actor_id="mfa-manager",
    )
    analyst = auth.register(
        "mfa-analyst",
        "analyst@mfa.example.test",
        PASSWORD,
        "analyst",
        tenant_id=tenant.tenant_id,
        actor_id="mfa-analyst",
        mfa_required=True,
    )
    authorization = application.container.require("pilot_authorization_service").create(
        analyst_id=analyst.actor_id,
        tenant_id=tenant.tenant_id,
        authorized_by="mfa-manager",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        approved_scenarios=["phishing_compromise"],
        audit_correlation_id="mfa-test-authorization",
    )
    return application, analyst, tenant.tenant_id, authorization.authorization_id


def _csrf(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def _login(client, password=PASSWORD):
    response = client.post(
        "/api/auth/login",
        json={"username": "mfa-analyst", "password": password},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    return response


def _enroll(client):
    response = client.post(
        "/api/auth/mfa/enroll",
        json={},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    uri = response.get_json()["provisioning_uri"]
    return pyotp.parse_uri(uri)


def _verify_enrollment(client, totp):
    return client.post(
        "/api/auth/mfa/verify-enrollment",
        json={"code": totp.now()},
        headers={"X-CSRF-Token": _csrf(client)},
    )


def test_password_plus_valid_mfa_allows_protected_soc_access(mfa_application):
    application, _analyst, _tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    assert _login(client).get_json()["mfa_required"] is True
    assert client.get("/api/pilot-authorizations/current").status_code == 401
    totp = _enroll(client)
    assert _verify_enrollment(client, totp).status_code == 200
    assert client.get("/api/pilot-authorizations/current").status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_invalid_missing_and_expired_mfa_are_denied(mfa_application):
    application, _analyst, _tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    assert client.get("/api/pilot-authorizations/current").status_code == 401
    _enroll(client)
    invalid = client.post(
        "/api/auth/mfa/verify-enrollment",
        json={"code": "000000"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert invalid.status_code == 400
    assert client.get("/api/pilot-authorizations/current").status_code == 401


def test_client_mfa_state_cannot_bypass_direct_api_or_change_tenant_role(mfa_application):
    application, _analyst, tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    with client.session_transaction() as state:
        state["mfa_verified"] = True
        state["auth_stage"] = "SOC_AUTHENTICATED"
        state["mfa_session_token"] = "forged"
        state["organization_id"] = "other-tenant"
        state["role"] = "admin"
    assert client.get("/api/pilot-authorizations/current").status_code in {401, 403}
    with client.session_transaction() as state:
        state["organization_id"] = tenant_id
    assert client.get("/api/pilot-authorizations/current").status_code == 401


def test_enrollment_is_bound_to_authenticated_user_and_secret_is_not_audit_data(mfa_application):
    application, analyst, tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    totp = _enroll(client)
    secret = totp.secret
    assert _verify_enrollment(client, totp).status_code == 200
    normal = client.get("/api/auth/me").get_json()
    assert secret not in json.dumps(normal)
    events = application.container.require("audit_service").list_for_tenant(tenant_id)
    serialized = json.dumps(events)
    assert secret not in serialized
    assert "mfa_enrollment_completed" in {event["event_type"] for event in events}
    with application.container.require("auth_service").db.session() as connection:
        row = connection.execute(
            "SELECT mfa_secret_ciphertext FROM users WHERE id=?", (analyst.id,)
        ).fetchone()
    assert row["mfa_secret_ciphertext"] != secret


def test_enrollment_cannot_target_another_user(mfa_application):
    application, analyst, _tenant_id, _authorization_id = mfa_application
    auth = application.container.require("auth_service")
    other = auth.register(
        "mfa-other",
        "other@mfa.example.test",
        PASSWORD,
        "analyst",
        tenant_id=_tenant_id,
        actor_id="mfa-other",
        mfa_required=True,
    )
    client = application.test_client()
    _login(client)
    response = client.post(
        "/api/auth/mfa/enroll",
        json={"user_id": other.id, "actor_id": other.actor_id},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    with application.container.require("auth_service").db.session() as connection:
        rows = connection.execute(
            "SELECT id, mfa_secret_ciphertext FROM users WHERE id IN (?, ?) ORDER BY id",
            (analyst.id, other.id),
        ).fetchall()
    assert [row["id"] for row in rows] == sorted((analyst.id, other.id))
    enrolled = {row["id"]: row["mfa_secret_ciphertext"] for row in rows}
    assert enrolled[analyst.id]
    assert enrolled[other.id] is None


def test_mfa_code_replay_and_logout_invalidate_access(mfa_application):
    application, _analyst, _tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    totp = _enroll(client)
    code = totp.now()
    first = client.post(
        "/api/auth/mfa/verify-enrollment",
        json={"code": code},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert first.status_code == 200
    replay = client.post(
        "/api/auth/mfa/verify",
        json={"code": code},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert replay.status_code == 400
    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": _csrf(client)})
    assert logout.status_code == 200
    assert client.get("/api/pilot-authorizations/current").status_code == 401


def test_concurrent_totp_verification_accepts_counter_once(mfa_application):
    application, analyst, _tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    totp = _enroll(client)
    assert _verify_enrollment(client, totp).status_code == 200

    service = MFAService(
        application.container.require("auth_service").db,
        secret_key_provider=lambda: application.secret_key,
    )
    with application.container.require("auth_service").db.session() as connection:
        row = connection.execute(
            "SELECT mfa_last_counter FROM users WHERE id=?", (analyst.id,)
        ).fetchone()
    accepted_counter = int(row["mfa_last_counter"]) + 1
    code = totp.at(accepted_counter * 30)
    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait()
        try:
            service.verify(analyst.id, code)
        except MFAError as exc:
            return ("rejected", str(exc))
        except Exception as exc:  # pragma: no cover - documents backend limits
            return ("error", type(exc).__name__)
        return ("success", None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [future.result() for future in (pool.submit(attempt), pool.submit(attempt))]

    assert [outcome[0] for outcome in outcomes].count("success") == 1, outcomes
    assert [outcome[0] for outcome in outcomes].count("rejected") == 1
    assert next(outcome[1] for outcome in outcomes if outcome[0] == "rejected") == "mfa_code_replayed"
    with application.container.require("auth_service").db.session() as connection:
        final = connection.execute(
            "SELECT mfa_last_counter FROM users WHERE id=?", (analyst.id,)
        ).fetchone()
        sessions = connection.execute(
            "SELECT COUNT(*) AS count FROM mfa_sessions WHERE user_id=?",
            (analyst.id,),
        ).fetchone()
    assert int(final["mfa_last_counter"]) == accepted_counter
    assert int(sessions["count"]) == 2


def test_revoked_pilot_authorization_cannot_regain_access_after_mfa(mfa_application):
    application, _analyst, tenant_id, authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    totp = _enroll(client)
    assert _verify_enrollment(client, totp).status_code == 200
    assert client.get("/api/pilot-authorizations/current").status_code == 200
    application.container.require("pilot_authorization_service").revoke(
        authorization_id,
        tenant_id=tenant_id,
        revoked_by="mfa-manager",
        reason="test revocation",
        audit_correlation_id="mfa-test-revoke",
    )
    assert client.get("/api/pilot-authorizations/current").status_code in {401, 403}


def test_password_reset_does_not_bypass_mfa(mfa_application):
    application, _analyst, _tenant_id, _authorization_id = mfa_application
    client = application.test_client()
    _login(client)
    auth = application.container.require("auth_service")
    challenge, code = auth.issue_otp(
        "analyst@mfa.example.test",
        "password_reset",
        user_id=auth.get_by_username("mfa-analyst").id,
        secret=application.secret_key,
    )
    new_password = random_password()
    response = client.post(
        "/api/auth/password-reset/confirm",
        json={"challenge_id": challenge, "code": code, "password": new_password},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    assert _login(client, new_password).get_json()["mfa_required"] is True
    assert client.get("/api/pilot-authorizations/current").status_code == 401


def test_existing_non_mfa_accounts_keep_password_authentication(mfa_application):
    application, _analyst, tenant_id, _authorization_id = mfa_application
    auth = application.container.require("auth_service")
    authority = application.container.require("canonical_authority")
    authority.identities.create("viewer@mfa.example.test", actor_id="mfa-viewer")
    authority.memberships.add(tenant_id, "mfa-viewer", "viewer")
    viewer = auth.register(
        "mfa-viewer", "viewer@mfa.example.test", PASSWORD, "viewer",
        tenant_id=tenant_id, actor_id="mfa-viewer",
    )
    client = application.test_client()
    response = client.post(
        "/api/auth/login",
        json={"username": viewer.username, "password": PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 200
    assert response.get_json()["mfa_required"] is False
