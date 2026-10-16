import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.credential_helpers import random_password
import dashboard.app as dashboard_app
import wsgi
from database.connection import DatabaseConnection, database
from database.migration_runner import MigrationRunner
from services.auth.auth_service import AuthService
from services.auth.mfa import MFAService
from services.auth.providers import TestEmailProvider
from services.audit.service import AuditService
from services.identity.canonical_authority import CanonicalAuthorityService


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _run_wsgi_startup(tmp_path, *, environment, secret_file=None, expected_secret=None):
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {
            "SENTINEL_DNA_ENV",
            "FLASK_ENV",
            "FLASK_DEBUG",
            "SENTINEL_DNA_SECRET_KEY",
            "SENTINEL_DNA_SECRET_KEY_FILE",
            "SENTINEL_DNA_SECURE_COOKIES",
            "SENTINEL_DNA_PILOT_ACCESS_REQUIRED",
            "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION",
            "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION",
            "SENTINEL_DNA_DB_PATH",
            "DATABASE_URL",
            "EXPECTED_WSGI_SECRET",
        }
    }
    env.update(
        SENTINEL_DNA_ENV=environment,
        SENTINEL_DNA_DB_PATH=str(tmp_path / "wsgi-startup.sqlite"),
    )
    if environment in {"staging", "production"}:
        env.update(
            FLASK_DEBUG="0",
            SENTINEL_DNA_SECURE_COOKIES="1",
            SENTINEL_DNA_PILOT_ACCESS_REQUIRED="1",
            SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION="external_non_production",
            SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION="disposable_staging",
            DATABASE_URL="postgresql://sentinel:synthetic@127.0.0.1:5432/sentinel_dna",
        )
    if secret_file is not None:
        env["SENTINEL_DNA_SECRET_KEY_FILE"] = str(secret_file)
    if expected_secret is not None:
        env["EXPECTED_WSGI_SECRET"] = expected_secret

    startup_script = """
import os
from database import connection
connection.database = connection.DatabaseConnection(os.environ["SENTINEL_DNA_DB_PATH"])
import wsgi
expected = os.environ.get("EXPECTED_WSGI_SECRET")
if expected is not None:
    assert wsgi.application.secret_key == expected
print("wsgi-startup-ok")
"""
    return subprocess.run(
        [sys.executable, "-c", startup_script],
        cwd=REPOSITORY_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_wsgi_startup_loads_valid_file_based_secret(tmp_path):
    secret = "synthetic-wsgi-secret-" + ("x" * 48)
    secret_file = tmp_path / "wsgi-secret.txt"
    secret_file.write_text(secret, encoding="utf-8")

    result = _run_wsgi_startup(
        tmp_path,
        environment="staging",
        secret_file=secret_file,
        expected_secret=secret,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "wsgi-startup-ok"


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_wsgi_startup_fails_closed_when_secret_is_missing(tmp_path, environment):
    result = _run_wsgi_startup(tmp_path, environment=environment)

    assert result.returncode != 0
    expected_error = (
        "SENTINEL_DNA_SECRET_KEY must be a non-placeholder staging secret"
        if environment == "staging"
        else "SENTINEL_DNA_SECRET_KEY must be configured for production"
    )
    assert expected_error in result.stderr
    assert "development-only-change-me" not in result.stderr


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_wsgi_startup_fails_closed_when_secret_is_weak(tmp_path, environment):
    secret_file = tmp_path / "weak-secret.txt"
    secret_file.write_text("short", encoding="utf-8")

    result = _run_wsgi_startup(
        tmp_path,
        environment=environment,
        secret_file=secret_file,
    )

    assert result.returncode != 0
    expected_error = (
        "SENTINEL_DNA_SECRET_KEY must be a non-placeholder staging secret"
        if environment == "staging"
        else "SENTINEL_DNA_SECRET_KEY must be configured for production"
    )
    assert expected_error in result.stderr
    assert "short" not in result.stderr


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_wsgi_startup_fails_closed_when_secret_file_is_unreadable(tmp_path, environment):
    secret_path = tmp_path / "secret-directory"
    secret_path.mkdir()

    result = _run_wsgi_startup(
        tmp_path,
        environment=environment,
        secret_file=secret_path,
    )

    assert result.returncode != 0
    assert "SENTINEL_DNA_SECRET_KEY_FILE must point to a readable secret file" in result.stderr
    assert "development-only-change-me" not in result.stderr


@pytest.fixture
def application(tmp_path, monkeypatch):
    db_path = tmp_path / "reconciliation.sqlite"
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)
    app = wsgi.application
    registry = app.container
    keys = ("auth_service", "canonical_authority", "mfa_service", "audit_service")
    previous = {key: registry.get(key) for key in keys}
    old_path = database.database_path
    db = DatabaseConnection(db_path)
    MigrationRunner(db).run()
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    audit = AuditService(db)
    registry.register("auth_service", auth)
    registry.register("canonical_authority", authority)
    registry.register("mfa_service", MFAService(db, secret_key_provider=lambda: app.secret_key, audit_service=audit))
    registry.register("audit_service", audit)
    database.database_path = str(db_path)
    coordinator = registry.require("investigation_coordinator")
    for service in vars(coordinator).values():
        ensure_schema = getattr(service, "_ensure_schema", None)
        if callable(ensure_schema):
            ensure_schema()
    config_keys = ("TESTING", "PILOT_ACCESS_REQUIRED", "EMAIL_PROVIDER", "SMS_PROVIDER", "ENVIRONMENT", "DEMO_DATA_ENABLED")
    old_config = {key: app.config.get(key) for key in config_keys}
    app.config.update(
        TESTING=True,
        PILOT_ACCESS_REQUIRED=False,
        EMAIL_PROVIDER=TestEmailProvider(),
        ENVIRONMENT="testing",
        DEMO_DATA_ENABLED=False,
    )
    try:
        yield app
    finally:
        for key, value in previous.items(): registry.register(key, value)
        for key, value in old_config.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value
        database.database_path = old_path


def register_and_login(client, username="reconciliation-user", email="reconciliation@example.test"):
    password = random_password()
    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    sent = client.post("/api/auth/email/send-registration-code", json={"email": email}, headers={"X-CSRF-Token": csrf})
    challenge = sent.get_json()["challenge_id"]
    code = client.application.config["EMAIL_PROVIDER"].messages[-1]["code"]
    assert client.post("/api/auth/email/verify-registration-code", json={"username": username, "email": email, "challenge_id": challenge, "code": code}, headers={"X-CSRF-Token": csrf}).status_code == 200
    payload = {"username": username, "email": email, "password": password, "date_of_birth": "1990-01-01", "email_challenge_id": challenge, "role": "admin", "tenant_id": "attacker"}
    assert client.post("/api/auth/register", json=payload, headers={"X-CSRF-Token": csrf}).status_code == 201
    response = client.post("/api/auth/login", json={"username": username, "password": password}, headers={"X-CSRF-Token": client.get("/api/auth/csrf").get_json()["csrf_token"]})
    assert response.status_code == 200


def test_wsgi_application_exposes_canonical_browser_entrypoints(application):
    client = application.test_client()
    assert client.get("/login").status_code == 200
    assert client.get("/signup").status_code == 200
    assert client.get("/").status_code == 401
    assert client.get("/workspace/").status_code == 401
    assert client.get("/workspace").status_code == 401
    assert client.get("/workspace/investigation/CASE-1").status_code == 401
    assert client.get("/workspace/investigation/CASE-1/report").status_code == 401


def test_production_deploys_only_the_canonical_wsgi_entrypoint():
    assert "from dashboard.app import app as application" in Path("wsgi.py").read_text(encoding="utf-8")
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
    assert client.get("/workspace").status_code == 200
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
    assert client.get("/workspace", headers={"X-Organization-ID": "attacker-tenant"}).status_code == 401
    assert client.get("/workspace/", headers={"X-Organization-ID": "attacker-tenant"}).status_code == 401
    register_and_login(client, "membership-user", "membership@example.test")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
        actor_id = state["actor_id"]
    with application.container.require("canonical_authority").db.session() as connection:
        connection.execute("DELETE FROM canonical_memberships WHERE tenant_id=? AND actor_id=?", (tenant_id, actor_id))
    assert client.get("/workspace").status_code == 401
    assert client.get("/workspace/").status_code == 401


def test_development_environment_has_no_investigation_auth_bypass(application):
    from services.core.security_context import authorize_investigation

    application.config["ENVIRONMENT"] = "development"
    with application.test_request_context("/api/investigations"):
        assert authorize_investigation({}, write=True) == (False, "authentication_required")


def test_wsgi_application_preserves_pilot_analyst_boundary(application):
    client = application.test_client()
    register_and_login(client, "pilot-boundary-user", "pilot-boundary@example.test")
    application.config["PILOT_ACCESS_REQUIRED"] = True

    response = client.get("/workspace/investigation/CASE-1")

    assert response.status_code == 403
    assert response.get_json() == {"error": "pilot_authorization_required"}
