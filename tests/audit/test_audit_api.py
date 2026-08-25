import json

import pytest
from tests.credential_helpers import random_password


PASSWORD = random_password()


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "audit_api.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")

    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def create_user(application, username, role):
    return application.container.require("auth_service").register(
        username,
        f"{username}@example.test",
        PASSWORD,
        role,
    )


def login(client, username):
    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200


def tenant_from_session(client):
    with client.session_transaction() as state:
        return state["organization_id"]


def record_event(application, tenant_id, event_type, details=None):
    return application.container.require("audit_service").record(
        event_type,
        tenant_id=tenant_id,
        actor_id=f"{tenant_id}-actor",
        operation="test",
        outcome="success",
        details=details or {},
    )


def test_unauthenticated_audit_read_is_denied(application):
    response = application.test_client().get("/api/admin/audit")

    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication_required"}


def test_analyst_without_audit_permission_is_denied(application):
    create_user(application, "audit-analyst", "analyst")
    client = application.test_client()
    login(client, "audit-analyst")

    response = client.get("/api/admin/audit")

    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


def test_public_registration_cannot_self_assign_audit_permission(application):
    client = application.test_client()
    response = client.post(
        "/api/auth/register",
        json={
            "username": "self-promoted-admin",
            "email": "self-promoted-admin@example.test",
            "password": PASSWORD,
            "role": "admin",
        },
    )

    assert response.status_code == 201
    login(client, "self-promoted-admin")
    audit_response = client.get("/api/admin/audit")
    assert audit_response.status_code == 403


@pytest.mark.parametrize("role", ["admin", "soc_manager"])
def test_privileged_audit_read_succeeds(application, role):
    username = f"audit-{role}"
    create_user(application, username, role)
    client = application.test_client()
    login(client, username)
    tenant_id = tenant_from_session(client)
    event_id = record_event(application, tenant_id, "PRIVILEGED_READ_TEST")

    response = client.get("/api/admin/audit?limit=20")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == "audit-read-v1"
    assert payload["limit"] == 20
    assert payload["count"] <= 20
    assert any(item["event_id"] == event_id for item in payload["events"])
    assert all(item["tenant_id"] == tenant_id for item in payload["events"])

    recorded = application.container.require("audit_service").list_for_tenant(tenant_id)
    assert any(item["event_type"] == "AUDIT_READ" for item in recorded)


def test_audit_read_is_tenant_scoped_and_ignores_tenant_override(application):
    create_user(application, "audit-admin-a", "admin")
    create_user(application, "audit-admin-b", "admin")

    client_a = application.test_client()
    client_b = application.test_client()
    login(client_a, "audit-admin-a")
    login(client_b, "audit-admin-b")

    tenant_a = tenant_from_session(client_a)
    tenant_b = tenant_from_session(client_b)
    event_a = record_event(application, tenant_a, "TENANT_A_EVENT")
    event_b = record_event(application, tenant_b, "TENANT_B_EVENT")

    response_a = client_a.get(f"/api/admin/audit?tenant_id={tenant_b}")
    response_b = client_b.get(f"/api/admin/audit?tenant_id={tenant_a}")

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    ids_a = {item["event_id"] for item in response_a.get_json()["events"]}
    ids_b = {item["event_id"] for item in response_b.get_json()["events"]}

    assert event_a in ids_a
    assert event_b not in ids_a
    assert event_b in ids_b
    assert event_a not in ids_b


def test_audit_read_is_bounded_and_deterministically_ordered(application):
    create_user(application, "audit-bounded-admin", "admin")
    client = application.test_client()
    login(client, "audit-bounded-admin")
    tenant_id = tenant_from_session(client)

    for index in range(105):
        record_event(application, tenant_id, f"BOUNDED_EVENT_{index}", {"sequence": index})

    response = client.get("/api/admin/audit?limit=100")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 100
    assert len(payload["events"]) == 100
    sequences = [item["details"].get("sequence") for item in payload["events"]]
    assert sequences == list(range(104, 4, -1))


@pytest.mark.parametrize("query", ["?limit=0", "?limit=101", "?limit=not-an-integer"])
def test_invalid_audit_limit_is_rejected(application, query):
    create_user(application, "audit-limit-admin", "admin")
    client = application.test_client()
    login(client, "audit-limit-admin")

    response = client.get(f"/api/admin/audit{query}")

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_limit"}


def test_audit_read_omits_sensitive_metadata(application):
    create_user(application, "audit-redaction-admin", "admin")
    client = application.test_client()
    login(client, "audit-redaction-admin")
    tenant_id = tenant_from_session(client)

    record_event(
        application,
        tenant_id,
        "SENSITIVE_METADATA_TEST",
        {
            "safe": "visible",
            "password": "must-not-return",
            "csrf_token": "must-not-return",
            "session_cookie": "must-not-return",
            "authorization_header": "must-not-return",
            "nested": {"bearer_token": "must-not-return"},
        },
    )

    response = client.get("/api/admin/audit")

    assert response.status_code == 200
    serialized = json.dumps(response.get_json()).lower()
    for forbidden in ("password", "csrf_token", "session_cookie", "authorization_header", "bearer_token"):
        assert forbidden not in serialized
    assert "safe" in serialized


def test_audit_read_does_not_leak_internal_exceptions(application, monkeypatch):
    create_user(application, "audit-error-admin", "admin")
    client = application.test_client()
    login(client, "audit-error-admin")

    def fail(*args, **kwargs):
        raise RuntimeError("database-secret-must-not-leak")

    monkeypatch.setattr(
        application.container.require("audit_read_service"),
        "list_for_tenant",
        fail,
    )

    response = client.get("/api/admin/audit")

    assert response.status_code == 503
    assert response.get_json() == {"error": "audit_read_unavailable"}
    assert b"database-secret-must-not-leak" not in response.data
