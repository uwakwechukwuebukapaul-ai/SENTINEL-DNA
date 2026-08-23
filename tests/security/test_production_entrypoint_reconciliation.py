import os
from pathlib import Path

import pytest


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "reconciliation.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def register_and_login(client, username="reconciliation-user", email="reconciliation@example.test"):
    assert client.post("/api/auth/register", json={"username": username, "email": email, "password": "CorrectHorseBattery1!", "role": "admin", "tenant_id": "attacker"}).status_code == 201
    response = client.post("/api/auth/login", json={"username": username, "password": "CorrectHorseBattery1!"}, headers={"X-CSRF-Token": client.get("/api/auth/csrf").get_json()["csrf_token"]})
    assert response.status_code == 200


def test_factory_exposes_canonical_browser_entrypoints(application):
    client = application.test_client()
    assert client.get("/login").status_code == 200
    assert client.get("/signup").status_code == 200
    assert client.get("/").status_code == 401
    assert client.get("/workspace/").status_code == 401
    assert client.get("/workspace/investigation/CASE-1").status_code == 401
    assert client.get("/workspace/investigation/CASE-1/report").status_code == 401


def test_production_deploys_only_the_canonical_wsgi_entrypoint():
    assert "from app import create_app" in Path("wsgi.py").read_text(encoding="utf-8")
    assert "application = create_app()" in Path("wsgi.py").read_text(encoding="utf-8")
    assert '"wsgi:application"' in Path("Dockerfile").read_text(encoding="utf-8")


def test_login_establishes_server_owned_canonical_context(application):
    client = application.test_client()
    register_and_login(client)
    with client.session_transaction() as state:
        assert state["user_id"]
        assert state["actor_id"]
        assert state["organization_id"].startswith("tenant-")
        assert state["canonical_principal"]["tenant_id"] == state["organization_id"]
    assert client.get("/").status_code == 200
    assert client.get("/profile").status_code == 200
    assert client.get("/workspace/").status_code == 200


def test_logout_requires_csrf_and_invalidates_session(application):
    client = application.test_client()
    register_and_login(client, "logout-user", "logout@example.test")
    assert client.post("/api/auth/logout").status_code == 403
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": token}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_arbitrary_organization_header_cannot_authorize_investigation(application):
    client = application.test_client()
    register_and_login(client, "tenant-user", "tenant@example.test")
    response = client.get("/api/investigations/CASE-1", headers={"X-Organization-ID": "unrelated-tenant"})
    assert response.status_code == 403


def test_missing_membership_and_unauthenticated_tenant_header_are_denied(application):
    client = application.test_client()
    assert client.get("/workspace/", headers={"X-Organization-ID": "attacker-tenant"}).status_code == 401
    register_and_login(client, "membership-user", "membership@example.test")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
        actor_id = state["actor_id"]
    with application.container.require("canonical_authority").db.session() as connection:
        connection.execute("DELETE FROM canonical_memberships WHERE tenant_id=? AND actor_id=?", (tenant_id, actor_id))
    assert client.get("/workspace/").status_code == 401


def test_development_environment_has_no_investigation_auth_bypass(application):
    from services.core.security_context import authorize_investigation

    application.config["ENVIRONMENT"] = "development"
    with application.test_request_context("/api/investigations"):
        assert authorize_investigation({}, write=True) == (False, "authentication_required")
