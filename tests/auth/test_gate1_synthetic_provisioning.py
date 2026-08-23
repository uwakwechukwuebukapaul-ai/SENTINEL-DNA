import importlib.util
import json
from pathlib import Path

import pytest

from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.gate1_synthetic_provisioning import (
    Gate1ProvisioningError,
    Gate1SyntheticProvisioningService,
    synthetic_identity_specs,
)
from services.identity.canonical_authority import CanonicalAuthorityService


TEST_REVISION = "a1" * 20


def build_services(tmp_path, monkeypatch, audit=None):
    db = DatabaseConnection(tmp_path / "gate1.sqlite")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db.database_path))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    audit = audit or AuditService(db)
    return db, auth, authority, Gate1SyntheticProvisioningService(auth, authority, audit, db, expected_revision=TEST_REVISION)


def test_guard_requires_explicit_production_release_authorization(monkeypatch):
    path = Path(__file__).parents[2] / "deployment" / "scripts" / "provision_gate1_synthetic_identities.py"
    spec = importlib.util.spec_from_file_location("gate1_provision_cli", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-secret")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(Path(__file__)))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    monkeypatch.delenv("SENTINEL_DNA_GATE1_PROVISIONING", raising=False)
    with pytest.raises(Gate1ProvisioningError, match="explicit_gate1_authorization_required"):
        module._guard(TEST_REVISION)


@pytest.mark.parametrize(
    ("environment", "revision", "secret", "db_path", "expected"),
    [
        ("staging", TEST_REVISION, "test-only-secret", str(Path(__file__)), "production_environment_required"),
        ("production", "not-a-full-revision", "test-only-secret", str(Path(__file__)), "full_release_revision_required"),
        ("production", TEST_REVISION, "", str(Path(__file__)), "protected_secret_configuration_required"),
        ("production", TEST_REVISION, "test-only-secret-value-0123456789", "", "database_path_configuration_required"),
        ("production", TEST_REVISION, "test-only-secret-value-0123456789", "/path/that/does/not/exist.sqlite", "database_path_unavailable"),
    ],
)
def test_guard_fails_closed_for_environment_release_and_required_configuration(
    monkeypatch, environment, revision, secret, db_path, expected
):
    path = Path(__file__).parents[2] / "deployment" / "scripts" / "provision_gate1_synthetic_identities.py"
    spec = importlib.util.spec_from_file_location("gate1_provision_cli_guards", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", environment)
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", secret)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", db_path)
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    with pytest.raises(Gate1ProvisioningError, match=expected):
        module._guard(revision)


def test_service_rechecks_authorization_outside_cli(tmp_path):
    db = DatabaseConnection(tmp_path / "guard.sqlite")
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    service = Gate1SyntheticProvisioningService(auth, authority, AuditService(db), db, expected_revision=TEST_REVISION)
    with pytest.raises(Gate1ProvisioningError, match="explicit_gate1_authorization_required"):
        service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})


def test_provision_creates_verified_canonical_identities_and_is_idempotent(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    passwords = {"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"}

    first = service.provision(passwords)
    second = service.provision(passwords)

    assert [item.state for item in first] == ["provisioned", "provisioned"]
    assert [item.state for item in second] == ["already_provisioned", "already_provisioned"]
    for spec in synthetic_identity_specs():
        user = auth.get_by_username(spec.username)
        assert user and user.is_active and user.email_verified_at and user.phone_verified_at
        assert auth.authenticate(spec.username, passwords[spec.lane]) is not None
        tenant, identity, membership = authority.resolve(spec.tenant_id, spec.actor_id)
        assert tenant.status == identity.status == membership.status == "active"
        assert membership.role == "analyst"


def test_refuses_to_overwrite_real_tenant_or_user(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    spec = synthetic_identity_specs()[0]
    authority.tenants.create("Real Tenant", spec.tenant_id)

    with pytest.raises(Gate1ProvisioningError, match="synthetic_tenant_conflict_A"):
        service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    assert auth.get_by_username(spec.username) is None


def test_transaction_rolls_back_all_identities_on_audit_failure(tmp_path, monkeypatch):
    class FailingAudit(AuditService):
        def __init__(self, db):
            super().__init__(db)
            self.calls = 0

        def record(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("controlled_test_failure")
            return super().record(*args, **kwargs)

    db = DatabaseConnection(tmp_path / "rollback.sqlite")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db.database_path))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    service = Gate1SyntheticProvisioningService(auth, authority, FailingAudit(db), db, expected_revision=TEST_REVISION)

    with pytest.raises(RuntimeError, match="controlled_test_failure"):
        service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    for spec in synthetic_identity_specs():
        assert auth.get_by_username(spec.username) is None
        assert authority.tenants.get(spec.tenant_id) is None
        assert authority.identities.get(spec.actor_id) is None


def test_cleanup_expires_only_marked_synthetic_identities_and_audits(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    unrelated = auth.register("unrelated-user", "unrelated@example.test", "UnrelatedPassword!123")

    cleaned = service.cleanup()

    assert [item.state for item in cleaned] == ["cleaned", "cleaned"]
    assert auth.get_by_username(unrelated.username).is_active
    for spec in synthetic_identity_specs():
        user = auth.get_by_username(spec.username)
        assert user is not None and not user.is_active
        assert authority.tenants.get(spec.tenant_id).status == "inactive"
        assert authority.identities.get(spec.actor_id).status == "inactive"
        assert authority.memberships.get(spec.tenant_id, spec.actor_id).status == "inactive"

    events = AuditService(db).list_for_tenant(synthetic_identity_specs()[0].tenant_id, limit=20)
    assert {event["event_type"] for event in events} == {"GATE1_SYNTHETIC_IDENTITY_PROVISIONED", "GATE1_SYNTHETIC_IDENTITY_REUSED", "GATE1_SYNTHETIC_IDENTITY_CLEANED"}
    assert all("password" not in json.dumps(event).lower() for event in events)


def test_cleanup_refuses_non_synthetic_identity_collision(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    spec = synthetic_identity_specs()[0]
    real_user = auth.register(spec.username, "real-owner@example.test", "RealOwnerPassword!123")

    with pytest.raises(Gate1ProvisioningError, match="synthetic_identity_conflict_A"):
        service.cleanup()
    assert auth.get_by_id(real_user.id).is_active


def test_provisioned_users_are_tenant_isolated_through_application_api(tmp_path, monkeypatch):
    from database.connection import database
    from app import create_app

    old_path = database.database_path
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "application.sqlite"))
    try:
        app = create_app()
        app.config.update(TESTING=True)
        auth = app.container.require("auth_service")
        authority = app.container.require("canonical_authority")
        audit = app.container.require("audit_service")
        service = Gate1SyntheticProvisioningService(auth, authority, audit, database, expected_revision=TEST_REVISION)
        passwords = {"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"}
        service.provision(passwords)

        clients = {}
        executions = {}
        for spec in synthetic_identity_specs():
            client = app.test_client()
            csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
            login = client.post(
                "/api/auth/login",
                json={"username": spec.username, "password": passwords[spec.lane]},
                headers={"X-CSRF-Token": csrf},
            )
            assert login.status_code == 200
            created = client.post(
                "/api/investigations",
                json={
                    "case_id": f"GATE1-APP-{spec.lane}",
                    "alert": {"source": "synthetic_gate1", "severity": "low"},
                    "artifacts": [{"type": "ip", "value": "192.0.2.10"}],
                },
            )
            assert created.status_code == 200
            listed = client.get("/api/investigations/executions")
            assert listed.status_code == 200
            execution = next(item for item in listed.get_json()["executions"] if item["case_id"] == f"GATE1-APP-{spec.lane}")
            clients[spec.lane] = client
            executions[spec.lane] = execution["execution_id"]

        assert clients["A"].get(f"/api/investigations/executions/{executions['A']}").status_code == 200
        assert clients["B"].get(f"/api/investigations/executions/{executions['B']}").status_code == 200
        assert clients["A"].get(f"/api/investigations/executions/{executions['B']}").status_code == 404
        assert clients["B"].get(f"/api/investigations/executions/{executions['A']}").status_code == 404
    finally:
        database.database_path = old_path
