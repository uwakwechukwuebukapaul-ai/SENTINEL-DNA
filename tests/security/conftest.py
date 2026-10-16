"""Shared isolated fixtures for canonical WSGI security workflow tests."""

import pytest

import dashboard.app as dashboard_app
import wsgi
from database.connection import DatabaseConnection, database
from database.migration_runner import MigrationRunner
from services.auth.auth_service import AuthService
from services.auth.mfa import MFAService
from services.auth.providers import TestEmailProvider, TestSMSProvider
from services.audit.service import AuditService
from services.identity.canonical_authority import CanonicalAuthorityService


@pytest.fixture
def canonical_application(tmp_path, monkeypatch):
    """Run WSGI routes against one isolated SQLite database and test providers."""
    db_path = tmp_path / "canonical-security.sqlite"
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setattr(dashboard_app, "DB_PATH", db_path)

    application = wsgi.application
    registry = application.container
    keys = ("auth_service", "canonical_authority", "mfa_service", "audit_service")
    previous = {key: registry.get(key) for key in keys}
    old_database_path = database.database_path
    old_config = {
        key: application.config.get(key)
        for key in (
            "TESTING", "PILOT_ACCESS_REQUIRED", "DEMO_DATA_ENABLED",
            "EMAIL_PROVIDER", "SMS_PROVIDER",
        )
    }

    db = DatabaseConnection(db_path)
    MigrationRunner(db).run()
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    audit = AuditService(db)
    email_provider = TestEmailProvider()
    sms_provider = TestSMSProvider()
    registry.register("auth_service", auth)
    registry.register("canonical_authority", authority)
    registry.register(
        "mfa_service",
        MFAService(db, secret_key_provider=lambda: application.secret_key, audit_service=audit),
    )
    registry.register("audit_service", audit)
    database.database_path = str(db_path)
    coordinator = registry.require("investigation_coordinator")
    # The WSGI container is process-global and was constructed before this
    # fixture selected its disposable database. Recreate only its own
    # repository schemas against the isolated path; never touch live data.
    for service in vars(coordinator).values():
        ensure_schema = getattr(service, "_ensure_schema", None)
        if callable(ensure_schema):
            ensure_schema()
    application.config.update(
        TESTING=True,
        PILOT_ACCESS_REQUIRED=False,
        DEMO_DATA_ENABLED=False,
        EMAIL_PROVIDER=email_provider,
        SMS_PROVIDER=sms_provider,
    )
    try:
        yield application
    finally:
        for key, value in previous.items():
            registry.register(key, value)
        for key, value in old_config.items():
            if value is None:
                application.config.pop(key, None)
            else:
                application.config[key] = value
        database.database_path = old_database_path


def register_and_login_analyst(client, username, email, *, registration_overrides=None):
    """Create an analyst through the same verified public path as the browser."""
    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    sent = client.post(
        "/api/auth/email/send-registration-code",
        json={"email": email},
        headers={"X-CSRF-Token": csrf},
    )
    assert sent.status_code == 202
    challenge_id = sent.get_json()["challenge_id"]
    email_provider = client.application.config["EMAIL_PROVIDER"]
    code = email_provider.messages[-1]["code"]
    verified = client.post(
        "/api/auth/email/verify-registration-code",
        json={"email": email, "challenge_id": challenge_id, "code": code},
        headers={"X-CSRF-Token": csrf},
    )
    assert verified.status_code == 200
    registration = {
        "username": username,
        "email": email,
        "password": "A7!x" + username + "-SafeDemoPassword",
        "date_of_birth": "1990-01-01",
        "email_challenge_id": challenge_id,
    }
    registration.update(registration_overrides or {})
    created = client.post(
        "/api/auth/register",
        json=registration,
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "A7!x" + username + "-SafeDemoPassword"},
    )
    assert logged_in.status_code == 200
    return logged_in
