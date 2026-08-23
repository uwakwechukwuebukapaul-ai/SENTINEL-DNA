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
    trusted_metadata = tmp_path / "gate1-release.json"
    trusted_metadata.write_text(json.dumps({"release_sha": TEST_REVISION, "image_digest": "sha256:" + "a" * 64}), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db.database_path))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    monkeypatch.setenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", str(trusted_metadata))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_DIGEST", "sha256:" + "a" * 64)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
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


def test_service_rechecks_authorization_outside_cli(tmp_path, monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_GATE1_PROVISIONING", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_GATE1_ROTATION", raising=False)
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


@pytest.mark.parametrize("role", ["admin", "soc_manager"])
def test_rotation_rejects_elevated_application_role_before_password_handling(tmp_path, monkeypatch, role):
    db, auth, _authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.cleanup()
    spec = synthetic_identity_specs()[0]
    with db.session() as connection:
        connection.execute("UPDATE users SET role=? WHERE username=?", (role, spec.username))
    _enable_rotation(monkeypatch)
    monkeypatch.setattr(service.auth, "reset_password", lambda *args, **kwargs: pytest.fail("password handling reached conflicting state"))

    assert service.inspect_rotation_state(("A",))[0].state == "conflicting_state"
    with pytest.raises(Gate1ProvisioningError, match="gate1_rotation_conflicting_state_A"):
        service.rotate_inactive({"A": "Gate1ReplacementA!456"}, lanes=("A",))


def test_rotation_accepts_analyst_application_and_membership_roles(tmp_path, monkeypatch):
    _db, auth, authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.cleanup()
    _enable_rotation(monkeypatch)
    spec = synthetic_identity_specs()[0]
    assert auth.get_by_username(spec.username).role == "analyst"
    assert authority.memberships.get(spec.tenant_id, spec.actor_id).role == "analyst"
    assert service.rotate_inactive({"A": "Gate1ReplacementA!456"}, lanes=("A",))[0].state == "rotated"


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
    trusted_metadata = tmp_path / "rollback-release.json"
    trusted_metadata.write_text(json.dumps({"release_sha": TEST_REVISION, "image_digest": "sha256:" + "a" * 64}), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", str(trusted_metadata))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_DIGEST", "sha256:" + "a" * 64)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
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
    trusted_metadata = tmp_path / "application-release.json"
    trusted_metadata.write_text(json.dumps({"release_sha": TEST_REVISION, "image_digest": "sha256:" + "a" * 64}), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", str(trusted_metadata))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_DIGEST", "sha256:" + "a" * 64)
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


def _enable_rotation(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_GATE1_ROTATION", "1")


def test_cleanup_then_guarded_rotation_reactivates_both_lanes(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    original = {"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"}
    replacement = {"A": "Gate1ReplacementA!456", "B": "Gate1ReplacementB!456"}
    service.provision(original)
    service.cleanup()
    _enable_rotation(monkeypatch)

    states = service.inspect_rotation_state()
    assert [item.state for item in states] == ["inactive_complete", "inactive_complete"]
    rotated = service.rotate_inactive(replacement)

    assert [item.state for item in rotated] == ["rotated", "rotated"]
    for spec in synthetic_identity_specs():
        user = auth.get_by_username(spec.username)
        assert user and user.is_active and user.session_version > 0
        assert auth.authenticate(spec.username, original[spec.lane]) is None
        assert auth.authenticate(spec.username, replacement[spec.lane]) is not None
        tenant, identity, membership = authority.resolve(spec.tenant_id, spec.actor_id)
        assert tenant.status == identity.status == membership.status == "active"


def test_rotation_can_select_one_lane_without_touching_the_other(tmp_path, monkeypatch):
    _db, auth, authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.cleanup()
    _enable_rotation(monkeypatch)

    service.rotate_inactive({"A": "Gate1ReplacementA!456"}, lanes=("A",))

    assert auth.get_by_username(synthetic_identity_specs()[0].username).is_active
    assert not auth.get_by_username(synthetic_identity_specs()[1].username).is_active
    assert authority.resolve(synthetic_identity_specs()[0].tenant_id, synthetic_identity_specs()[0].actor_id)[0].status == "active"
    assert authority.tenants.get(synthetic_identity_specs()[1].tenant_id).status == "inactive"


def test_rotation_rejects_missing_state_and_requires_separate_rotation_authorization(tmp_path, monkeypatch):
    _db, _auth, _authority, service = build_services(tmp_path, monkeypatch)
    _enable_rotation(monkeypatch)

    assert service.inspect_rotation_state(("A",))[0].state == "absent"
    with pytest.raises(Gate1ProvisioningError, match="gate1_rotation_absent_A"):
        service.rotate_inactive({"A": "Gate1ReplacementA!456"}, lanes=("A",))

    monkeypatch.delenv("SENTINEL_DNA_GATE1_ROTATION", raising=False)
    with pytest.raises(Gate1ProvisioningError, match="explicit_gate1_rotation_authorization_required"):
        service.inspect_rotation_state(("A",))


def test_rotation_rejects_conflicting_and_cross_tenant_graphs(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.cleanup()
    _enable_rotation(monkeypatch)
    spec = synthetic_identity_specs()[0]

    with db.session() as connection:
        connection.execute("UPDATE users SET tenant_id=? WHERE username=?", ("unexpected-tenant", spec.username))
    assert service.inspect_rotation_state(("A",))[0].state == "conflicting_state"
    with pytest.raises(Gate1ProvisioningError, match="gate1_rotation_conflicting_state_A"):
        service.rotate_inactive({"A": "Gate1ReplacementA!456"}, lanes=("A",))

    with db.session() as connection:
        connection.execute("UPDATE users SET tenant_id=? WHERE username=?", (spec.tenant_id, spec.username))
    extra_tenant = authority.tenants.create("Gate1 unexpected tenant", "gate1-unexpected-tenant")
    authority.memberships.add(extra_tenant.tenant_id, spec.actor_id, "analyst")
    assert service.inspect_rotation_state(("A",))[0].state == "conflicting_state"


def test_repeated_rotation_requires_another_cleanup(tmp_path, monkeypatch):
    _db, _auth, _authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.cleanup()
    _enable_rotation(monkeypatch)
    replacement = {"A": "Gate1ReplacementA!456", "B": "Gate1ReplacementB!456"}
    service.rotate_inactive(replacement)

    assert service.inspect_rotation_state()[0].state == "active_complete"
    with pytest.raises(Gate1ProvisioningError, match="gate1_rotation_active_complete_A"):
        service.rotate_inactive(replacement)


def _load_gate1_cli():
    path = Path(__file__).parents[2] / "deployment" / "scripts" / "provision_gate1_synthetic_identities.py"
    spec = importlib.util.spec_from_file_location("gate1_provision_cli_rotation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rotation_cli_requires_separate_flag(tmp_path, monkeypatch):
    db = DatabaseConnection(tmp_path / "cli-guard.sqlite")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db.database_path))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    monkeypatch.delenv("SENTINEL_DNA_GATE1_ROTATION", raising=False)

    assert _load_gate1_cli().main(["rotate", "--expected-revision", TEST_REVISION]) == 2


def test_rotation_cli_validates_state_before_hidden_prompt(tmp_path, monkeypatch):
    db, _auth, _authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    _enable_rotation(monkeypatch)
    module = _load_gate1_cli()
    monkeypatch.setattr(module, "_rotation_passwords", lambda _lanes: pytest.fail("password prompt reached invalid state"))

    assert module.main(["rotate", "--expected-revision", TEST_REVISION]) == 2


def test_rotation_fails_closed_for_mixed_and_partial_state(tmp_path, monkeypatch):
    db, auth, authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    _enable_rotation(monkeypatch)

    auth.deactivate_user(auth.get_by_username(synthetic_identity_specs()[0].username).id)
    assert service.inspect_rotation_state(("A",))[0].state == "mixed_state"
    with pytest.raises(Gate1ProvisioningError, match="gate1_rotation_mixed_state_A"):
        service.rotate_inactive({"A": "Gate1ReplacementA!456"}, lanes=("A",))

    spec = synthetic_identity_specs()[1]
    with db.session() as connection:
        connection.execute("DELETE FROM canonical_memberships WHERE tenant_id=? AND actor_id=?", (spec.tenant_id, spec.actor_id))
    assert service.inspect_rotation_state(("B",))[0].state == "partial_state"
    with pytest.raises(Gate1ProvisioningError, match="gate1_rotation_partial_state_B"):
        service.rotate_inactive({"B": "Gate1ReplacementB!456"}, lanes=("B",))
    assert authority.tenants.get(spec.tenant_id).status == "active"


def test_ordinary_provision_rejects_complete_inactive_state(tmp_path, monkeypatch):
    _db, _auth, _authority, service = build_services(tmp_path, monkeypatch)
    passwords = {"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"}
    service.provision(passwords)
    service.cleanup()

    with pytest.raises(Gate1ProvisioningError, match="synthetic_identity_partial_state_requires_review"):
        service.provision(passwords)


def test_rotation_revokes_persistent_sessions_and_audits_each_lane(tmp_path, monkeypatch):
    db, auth, _authority, service = build_services(tmp_path, monkeypatch)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    for spec in synthetic_identity_specs():
        auth.create_persistent_session(
            auth.get_by_username(spec.username),
            f"session-token-{spec.lane}",
            spec.tenant_id,
            f"session-{spec.lane}",
            "2099-01-01T00:00:00+00:00",
        )
    service.cleanup()
    _enable_rotation(monkeypatch)
    service.rotate_inactive({"A": "Gate1ReplacementA!456", "B": "Gate1ReplacementB!456"})

    for spec in synthetic_identity_specs():
        user = auth.get_by_username(spec.username)
        assert auth.list_sessions(user.id) == []
    events = AuditService(db).list_for_tenant(synthetic_identity_specs()[0].tenant_id, event_type="GATE1_SYNTHETIC_IDENTITY_ROTATED", limit=10)
    assert len(events) == 1
    assert events[0]["operation"] == "rotate_inactive"
    assert "password" not in json.dumps(events).lower()


def test_rotation_audit_failure_rolls_back_every_selected_lane(tmp_path, monkeypatch):
    class RotationAuditFailure(AuditService):
        def record(self, event_type, *args, **kwargs):
            if event_type == "GATE1_SYNTHETIC_IDENTITY_ROTATED":
                raise RuntimeError("controlled_rotation_audit_failure")
            return super().record(event_type, *args, **kwargs)

    db = DatabaseConnection(tmp_path / "rotation-rollback.sqlite")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db.database_path))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    trusted_metadata = tmp_path / "rotation-rollback-release.json"
    trusted_metadata.write_text(json.dumps({"release_sha": TEST_REVISION, "image_digest": "sha256:" + "a" * 64}), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", str(trusted_metadata))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_DIGEST", "sha256:" + "a" * 64)
    _enable_rotation(monkeypatch)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    service = Gate1SyntheticProvisioningService(auth, authority, RotationAuditFailure(db), db, expected_revision=TEST_REVISION)
    service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
    service.cleanup()

    with pytest.raises(RuntimeError, match="controlled_rotation_audit_failure"):
        service.rotate_inactive({"A": "Gate1ReplacementA!456", "B": "Gate1ReplacementB!456"})

    assert [item.state for item in service.inspect_rotation_state()] == ["inactive_complete", "inactive_complete"]
    for spec in synthetic_identity_specs():
        assert not auth.get_by_username(spec.username).is_active


def test_rotation_invalidates_existing_signed_session_epoch(tmp_path, monkeypatch):
    from database.connection import database
    from app import create_app

    old_path = database.database_path
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_PROVISIONING", "1")
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", TEST_REVISION)
    trusted_metadata = tmp_path / "session-epoch-release.json"
    trusted_metadata.write_text(json.dumps({"release_sha": TEST_REVISION, "image_digest": "sha256:" + "a" * 64}), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", str(trusted_metadata))
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_DIGEST", "sha256:" + "a" * 64)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "session-epoch.sqlite"))
    try:
        app = create_app()
        app.config.update(TESTING=True)
        auth = app.container.require("auth_service")
        authority = app.container.require("canonical_authority")
        audit = app.container.require("audit_service")
        service = Gate1SyntheticProvisioningService(auth, authority, audit, database, expected_revision=TEST_REVISION)
        original = {"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"}
        service.provision(original)
        client = app.test_client()
        csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
        assert client.post(
            "/api/auth/login",
            json={"username": synthetic_identity_specs()[0].username, "password": original["A"]},
            headers={"X-CSRF-Token": csrf},
        ).status_code == 200
        service.cleanup()
        _enable_rotation(monkeypatch)
        service.rotate_inactive({"A": "Gate1ReplacementA!456", "B": "Gate1ReplacementB!456"})

        assert client.get("/api/auth/me").status_code == 401
    finally:
        database.database_path = old_path


def test_user_deactivation_and_reactivation_do_not_restore_signed_session(tmp_path, monkeypatch):
    from database.connection import database
    from app import create_app

    old_path = database.database_path
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "user-lifecycle.sqlite"))
    try:
        app = create_app()
        app.config.update(TESTING=True)
        auth = app.container.require("auth_service")
        user = auth.register("lifecycle-user", "lifecycle@example.test", "LifecyclePassword!123")
        client = app.test_client()
        csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
        assert client.post("/api/auth/login", json={"username": user.username, "password": "LifecyclePassword!123"}, headers={"X-CSRF-Token": csrf}).status_code == 200
        assert auth.deactivate_user(user.id)
        assert auth.activate_user(user.id)
        assert client.get("/api/auth/me").status_code == 401
    finally:
        database.database_path = old_path


def test_tenant_deactivation_and_reactivation_do_not_restore_signed_session(tmp_path, monkeypatch):
    from database.connection import database
    from app import create_app

    old_path = database.database_path
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "test-only-gate1-secret-value-0123456789")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "tenant-lifecycle.sqlite"))
    try:
        app = create_app()
        app.config.update(TESTING=True)
        auth = app.container.require("auth_service")
        authority = app.container.require("canonical_authority")
        user = auth.register("tenant-lifecycle-user", "tenant-lifecycle@example.test", "LifecyclePassword!123")
        tenant = authority.tenants.create("Lifecycle Tenant", "tenant-lifecycle")
        identity = authority.identities.create(user.email, user.username, "tenant-lifecycle-actor")
        authority.memberships.add(tenant.tenant_id, identity.actor_id, "analyst")
        with auth.db.session() as connection:
            connection.execute("UPDATE users SET tenant_id=?, actor_id=? WHERE id=?", (tenant.tenant_id, identity.actor_id, user.id))
        client = app.test_client()
        csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
        assert client.post("/api/auth/login", json={"username": user.username, "password": "LifecyclePassword!123"}, headers={"X-CSRF-Token": csrf}).status_code == 200
        authority.tenants.set_status(tenant.tenant_id, "inactive")
        authority.tenants.set_status(tenant.tenant_id, "active")
        assert client.get("/api/auth/me").status_code == 401
    finally:
        database.database_path = old_path


def test_release_guard_requires_trusted_revision_and_digest_metadata(tmp_path, monkeypatch):
    _db, _auth, _authority, service = build_services(tmp_path, monkeypatch)
    monkeypatch.delenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH")
    with pytest.raises(Gate1ProvisioningError, match="trusted_release_metadata_required"):
        service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})

    metadata = tmp_path / "wrong-release.json"
    metadata.write_text(json.dumps({"release_sha": "b2" * 20, "image_digest": "sha256:" + "a" * 64}), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH", str(metadata))
    with pytest.raises(Gate1ProvisioningError, match="trusted_release_revision_mismatch"):
        service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})

    metadata.write_text(json.dumps({"release_sha": TEST_REVISION, "image_digest": "sha256:" + "b" * 64}), encoding="utf-8")
    with pytest.raises(Gate1ProvisioningError, match="image_digest_mismatch"):
        service.provision({"A": "Gate1SyntheticA!123", "B": "Gate1SyntheticB!123"})
