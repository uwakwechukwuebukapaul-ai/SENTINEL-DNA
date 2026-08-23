import importlib.util
import json
from pathlib import Path

import pytest

from database.connection import DatabaseConnection
from database.connection import database
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.privileged_provisioning import (
    PrivilegedIdentityProvisioningService,
    PrivilegedProvisioningError,
)
from services.identity.canonical_authority import CanonicalAuthorityService


PASSWORD = "StrongBootstrapPassword!123"
TEST_REVISION = "d6" * 20


def services_for(tmp_path):
    db = DatabaseConnection(tmp_path / "privileged.sqlite")
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    audit = AuditService(db)
    tenant = authority.tenants.create("Gate 1 Tenant", "gate1-tenant")
    service = PrivilegedIdentityProvisioningService(auth, authority, audit, db)
    return db, auth, authority, audit, tenant, service


@pytest.mark.parametrize("role", ["admin", "soc_manager"])
def test_provisions_privileged_identity_with_canonical_tenant_and_audit(tmp_path, role):
    db, auth, authority, audit, tenant, service = services_for(tmp_path)

    result = service.provision(
        username=f"gate1-{role}",
        email=f"gate1-{role}@example.test",
        tenant_id=tenant.tenant_id,
        role=role,
        password=PASSWORD,
        password_confirmation=PASSWORD,
    )

    user = auth.get_by_username(result.username)
    assert user is not None
    assert user.role == role
    assert user.tenant_id == tenant.tenant_id
    assert user.actor_id == result.actor_id
    assert auth.authenticate(result.username, PASSWORD) is not None

    resolved_tenant, identity, membership = authority.resolve(tenant.tenant_id, result.actor_id)
    assert resolved_tenant.tenant_id == tenant.tenant_id
    assert identity.actor_id == result.actor_id
    assert membership.role == role

    events = audit.list_for_tenant(tenant.tenant_id)
    event = next(item for item in events if item["event_type"] == "PRIVILEGED_IDENTITY_PROVISIONED")
    assert event["operation"] == "provision"
    assert event["outcome"] == "success"
    assert event["actor_id"] == "operator:privileged-bootstrap"
    assert event["details"]["role"] == role
    serialized = json.dumps(event).lower()
    assert "password" not in serialized
    assert "password_hash" not in serialized


def test_rejects_analyst_role(tmp_path):
    _, _, _, _, tenant, service = services_for(tmp_path)

    with pytest.raises(PrivilegedProvisioningError, match="invalid_privileged_role"):
        service.provision(
            username="not-privileged",
            email="not-privileged@example.test",
            tenant_id=tenant.tenant_id,
            role="analyst",
            password=PASSWORD,
            password_confirmation=PASSWORD,
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("tenant_id", "", "invalid_tenant"),
        ("tenant_id", "missing-tenant", "invalid_tenant"),
        ("username", "bad space", "invalid_username"),
        ("email", "not-an-email", "invalid_email"),
        ("password", "short", "invalid_password"),
        ("password", "          ", "invalid_password"),
    ],
)
def test_rejects_invalid_input(tmp_path, field, value, error):
    _, _, _, _, tenant, service = services_for(tmp_path)
    values = {
        "username": "valid-bootstrap",
        "email": "valid-bootstrap@example.test",
        "tenant_id": tenant.tenant_id,
        "role": "admin",
        "password": PASSWORD,
        "password_confirmation": PASSWORD,
    }
    values[field] = value
    with pytest.raises(PrivilegedProvisioningError, match=error):
        service.provision(**values)


def test_rejects_password_mismatch_and_duplicate_username(tmp_path):
    _, _, _, _, tenant, service = services_for(tmp_path)
    values = {
        "username": "duplicate-bootstrap",
        "email": "duplicate-bootstrap@example.test",
        "tenant_id": tenant.tenant_id,
        "role": "admin",
        "password": PASSWORD,
        "password_confirmation": "DifferentStrongPassword!123",
    }
    with pytest.raises(PrivilegedProvisioningError, match="password_confirmation_mismatch"):
        service.provision(**values)

    values["password_confirmation"] = PASSWORD
    service.provision(**values)
    with pytest.raises(PrivilegedProvisioningError, match="identity_already_exists"):
        service.provision(**values)


def test_cli_requires_guard_and_never_prints_password(tmp_path, monkeypatch, capsys):
    path = Path(__file__).parents[2] / "deployment" / "scripts" / "provision_privileged_identity.py"
    spec = importlib.util.spec_from_file_location("privileged_bootstrap_cli", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setenv("SENTINEL_DNA_PRIVILEGED_BOOTSTRAP", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-bootstrap-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "cli.sqlite"))
    AuthService(DatabaseConnection(tmp_path / "cli.sqlite"))
    monkeypatch.setattr(module, "input", lambda _: "n", raising=False)

    result = module.main(
        [
            "--username", "bootstrap-admin",
            "--email", "bootstrap-admin@example.test",
            "--tenant", "missing-tenant",
            "--role", "admin",
            "--expected-revision", TEST_REVISION,
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Provisioning cancelled." in captured.out
    assert PASSWORD not in captured.out
    assert PASSWORD not in captured.err


def test_cli_success_does_not_print_password_or_hash(tmp_path, monkeypatch, capsys):
    path = Path(__file__).parents[2] / "deployment" / "scripts" / "provision_privileged_identity.py"
    spec = importlib.util.spec_from_file_location("privileged_bootstrap_cli_success", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    db_path = tmp_path / "cli-success.sqlite"
    db = DatabaseConnection(db_path)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    audit = AuditService(db)
    authority.tenants.create("CLI Tenant", "cli-tenant")

    monkeypatch.setenv("SENTINEL_DNA_PRIVILEGED_BOOTSTRAP", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-bootstrap-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))
    monkeypatch.setattr(module, "input", lambda _: "y", raising=False)
    monkeypatch.setattr(module.getpass, "getpass", lambda _: PASSWORD)

    result = module.main(
        [
            "--username", "cli-bootstrap-admin",
            "--email", "cli-bootstrap-admin@example.test",
            "--tenant", "cli-tenant",
            "--role", "admin",
            "--expected-revision", TEST_REVISION,
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Privileged identity provisioned" in captured.out
    assert PASSWORD not in captured.out
    assert PASSWORD not in captured.err
    assert "password_hash" not in captured.out.lower()


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "http.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def _login(client, username, password):
    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["admin", "soc_manager"])
def test_provisioned_privileged_identity_authorizes_audit_api(application, role):
    auth = application.container.require("auth_service")
    authority = application.container.require("canonical_authority")
    audit = application.container.require("audit_service")
    tenant = authority.tenants.create(f"HTTP {role} Tenant", f"http-{role}-tenant")
    service = PrivilegedIdentityProvisioningService(auth, authority, audit, database)
    username = f"http-{role}-bootstrap"
    email = f"{username}@example.test"

    result = service.provision(
        username=username,
        email=email,
        tenant_id=tenant.tenant_id,
        role=role,
        password=PASSWORD,
        password_confirmation=PASSWORD,
    )

    client = application.test_client()
    _login(client, result.username, PASSWORD)
    response = client.get("/api/admin/audit")
    assert response.status_code == 200
    assert response.get_json()["version"] == "audit-read-v1"


def test_analyst_and_unauthenticated_remain_denied(application):
    client = application.test_client()
    assert client.get("/api/admin/audit").status_code == 401

    analyst = application.container.require("auth_service").register(
        "http-analyst",
        "http-analyst@example.test",
        PASSWORD,
    )
    _login(client, analyst.username, PASSWORD)
    assert client.get("/api/admin/audit").status_code == 403


def test_cli_rejects_missing_operator_guard(monkeypatch, capsys):
    path = Path(__file__).parents[2] / "deployment" / "scripts" / "provision_privileged_identity.py"
    spec = importlib.util.spec_from_file_location("privileged_bootstrap_cli_guard", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.delenv("SENTINEL_DNA_PRIVILEGED_BOOTSTRAP", raising=False)

    result = module.main(
        [
            "--username", "bootstrap-admin",
            "--email", "bootstrap-admin@example.test",
            "--tenant", "tenant-a",
            "--role", "admin",
            "--expected-revision", TEST_REVISION,
        ]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "explicit_privileged_bootstrap_required" in captured.err
    assert "Password" not in captured.out
