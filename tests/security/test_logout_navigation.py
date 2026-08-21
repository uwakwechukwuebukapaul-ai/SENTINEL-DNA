import pytest


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "logout-navigation.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    from app import create_app

    app = create_app()
    app.config.update(TESTING=True, DEMO_DATA_ENABLED=True)
    return app


def login(client):
    assert client.post(
        "/api/auth/register",
        json={"username": "logout-navigation", "email": "logout-navigation@example.test", "password": "CorrectHorseBattery1!"},
    ).status_code == 201
    assert client.post(
        "/api/auth/login",
        json={"username": "logout-navigation", "password": "CorrectHorseBattery1!"},
    ).status_code == 200


def test_authenticated_pages_render_shared_logout_navigation(application):
    client = application.test_client()
    assert b"Sign out" not in client.get("/login").data
    login(client)
    assert b"Sign out" in client.get("/").data
    assert b"Sign out" in client.get("/profile").data
    workspace = client.get("/workspace/")
    assert b"Sign out" in workspace.data
    case_id = next(iter(application.container.require("investigation_coordinator").get_workspace_snapshot("tenant-1")["investigations"]), {}).get("case_id")
    if not case_id:
        with client.session_transaction() as state:
            case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(state["organization_id"])
    assert b"Sign out" in client.get(f"/workspace/investigation/{case_id}").data
    assert b"Sign out" in client.get(f"/workspace/investigation/{case_id}/report").data


def test_browser_logout_requires_csrf_redirects_and_invalidates_session(application):
    client = application.test_client()
    login(client)
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
        json={"username": "logout-navigation", "password": "CorrectHorseBattery1!"},
    ).status_code == 200
