import pytest
from tests.security.conftest import register_and_login_analyst


@pytest.fixture
def application(canonical_application):
    canonical_application.config["DEMO_DATA_ENABLED"] = True
    return canonical_application


def test_authenticated_pages_render_shared_logout_navigation(application):
    client = application.test_client()
    assert b"Sign out" not in client.get("/login").data
    register_and_login_analyst(client, "logout-navigation", "logout-navigation@example.test")
    assert b"Sign out" in client.get("/").data
    assert b"Sign out" in client.get("/profile").data
    workspace = client.get("/workspace/")
    assert b"Sign out" in workspace.data
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(tenant_id)
    assert b"Sign out" in client.get(f"/workspace/investigation/{case_id}").data
    assert b"Sign out" in client.get(f"/workspace/investigation/{case_id}/report").data


def test_browser_logout_requires_csrf_redirects_and_invalidates_session(application):
    client = application.test_client()
    register_and_login_analyst(client, "logout-navigation", "logout-navigation@example.test")
    assert client.post("/api/auth/logout", data={}).status_code == 403
    assert client.get("/api/auth/me").status_code == 200

    with client.session_transaction() as state:
        csrf_token = state["csrf_token"]
    response = client.post("/api/auth/logout", data={"csrf_token": csrf_token}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?signed_out=true")
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/").status_code == 401
    assert b"You have been signed out." in client.get(response.headers["Location"]).data

    assert client.post(
        "/api/auth/login",
        json={"username": "logout-navigation", "password": "A7!xlogout-navigation-SafeDemoPassword"},
    ).status_code == 200
