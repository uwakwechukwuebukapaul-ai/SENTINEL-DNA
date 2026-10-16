import os
import pytest

import dashboard.app as dashboard_app
from database.connection import DatabaseConnection, database
from database.migration_runner import MigrationRunner
from services.auth.auth_service import AuthService
from services.auth.mfa import MFAService
from services.auth.providers import TestEmailProvider
from services.identity.canonical_authority import CanonicalAuthorityService
from tests.credential_helpers import random_password


@pytest.fixture()
def client(tmp_path, monkeypatch):

    db_path = tmp_path / "auth_test.db"

    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)

    app = dashboard_app.app
    registry = app.container
    keys = ("auth_service", "canonical_authority", "mfa_service")
    previous = {key: registry.get(key) for key in keys}
    old_path = database.database_path
    old_config = {key: app.config.get(key) for key in ("TESTING", "PILOT_ACCESS_REQUIRED", "EMAIL_PROVIDER")}
    db = DatabaseConnection(db_path)
    MigrationRunner(db).run()
    auth = AuthService(db)
    registry.register("auth_service", auth)
    registry.register("canonical_authority", CanonicalAuthorityService(db, auth=auth))
    registry.register("mfa_service", MFAService(db, secret_key_provider=lambda: app.secret_key))
    app.config.update(TESTING=True, PILOT_ACCESS_REQUIRED=False, EMAIL_PROVIDER=TestEmailProvider())

    with app.test_client() as client:
        try:
            yield client
        finally:
            for key, value in previous.items(): registry.register(key, value)
            app.config.update(old_config)
            database.database_path = old_path


def test_auth_session_and_csrf(client):

    username = "security-test-user"
    password = random_password()

    email = f"{username}@example.test"
    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    sent = client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    challenge = sent.get_json()["challenge_id"]
    code = client.application.config["EMAIL_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/email/verify-registration-code", json={"email": email, "challenge_id": challenge, "code": code}, headers={"X-CSRF-Token": csrf}).status_code == 200
    response = client.post("/api/auth/register", json={"username": username, "email": email, "password": password, "date_of_birth": "1990-01-01", "email_challenge_id": challenge}, headers={"X-CSRF-Token": csrf})

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
