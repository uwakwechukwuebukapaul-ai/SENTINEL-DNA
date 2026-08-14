import os
import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):

    db_path = tmp_path / "auth_test.db"

    os.environ["SENTINEL_DNA_DB_PATH"] = str(db_path)

    app = create_app()

    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_auth_session_and_csrf(client):

    username = "security-test-user"

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.test",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code in (200, 201)

    login = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "StrongPassword123!",
        },
    )

    assert login.status_code == 200

    csrf = client.get("/api/auth/csrf")

    assert csrf.status_code == 200
