import pytest

pytest.importorskip("flask")

from dashboard.app import app


def test_auth_session_and_csrf():
    app.config["TESTING"] = True
    client = app.test_client()
    username = "security-test-user"
    response = client.post("/api/auth/register", json={"username": username, "email": f"{username}@example.test", "password": "StrongPassword123!"})
    assert response.status_code in (201, 409)
    login = client.post("/api/auth/login", json={"username": username, "password": "StrongPassword123!"})
    assert login.status_code == 200
    with client.session_transaction() as state:
        token = state["csrf_token"]
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": token}).status_code == 200
