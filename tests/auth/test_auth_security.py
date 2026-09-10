import os
import pytest

from app import create_app
from tests.credential_helpers import random_password


@pytest.fixture()
def client(tmp_path, monkeypatch):

    db_path = tmp_path / "auth_test.db"

    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))

    app = create_app()

    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_auth_session_and_csrf(client):

    username = "security-test-user"
    password = random_password()

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.test",
            "password": password,
        },
    )

    assert response.status_code in (200, 201)

    login = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert login.status_code == 200

    csrf = client.get("/api/auth/csrf")

    assert csrf.status_code == 200


def test_inactive_users_are_hidden_from_authentication_lookups_and_login(client):
    password = random_password()
    auth = client.application.container.require("auth_service")
    user = auth.register(
        "inactive-lookup-user",
        "inactive-lookup@example.test",
        password,
    )

    assert auth.get_by_username(user.username).id == user.id
    assert auth.deactivate_user(user.id) is True
    assert auth.get_by_username(user.username) is None
    inactive = auth.get_by_username(user.username, include_inactive=True)
    assert inactive is not None and inactive.id == user.id and not inactive.is_active
    assert auth.authenticate(user.username, password) is None
    assert auth.authenticate(user.email, password) is None
