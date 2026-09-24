"""Isolated tests for the local two-human ceremony coordinator."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from database.connection import DatabaseConnection
from database.migration_runner import MigrationRunner
from database.migrations.registry import (
    apply_staging_authority_enrollment_namespace,
    apply_staging_two_human_ceremony_namespace,
)
from services.audit.service import AuditService
from services.auth.local_two_human_staging_ceremony import (
    EXPECTED_RELEASE,
    LocalTwoHumanCeremonyError,
    LocalTwoHumanStagingCeremony,
    verify_final_artifact,
)
from services.auth.staging_authority_enrollment import PAYLOAD_FIELDS, SIGNATURE_DOMAIN, _canonical


def _raw_public(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class FakeAuth:
    def __init__(self, users):
        self.users = users

    def session_user(self, user_id, _version):
        return self.users.get(user_id)


class FakeMFA:
    def __init__(self, valid=True):
        self.valid = valid

    def session_verified(self, _user_id, token, *, session_version, tenant_id):
        return self.valid and bool(token) and session_version == 1 and tenant_id in {"control-tenant", "tenant-a", "tenant-b"}


def _user(user_id, actor_id, tenant_id="control-tenant"):
    return SimpleNamespace(id=user_id, actor_id=actor_id, tenant_id=tenant_id, mfa_required=True)


def _release(authority="authority-demo", tenant="control-tenant"):
    return dict(EXPECTED_RELEASE, authority_id=authority, control_tenant_id=tenant)


def _session(user_id, token, tenant_id="control-tenant"):
    return {
        "user_id": user_id, "session_version": 1, "organization_id": tenant_id,
        "mfa_session_token": token,
    }


@pytest.fixture
def ceremony_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    monkeypatch.setenv("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "disposable_staging")
    db = DatabaseConnection(tmp_path / "ceremony.sqlite")
    MigrationRunner(db).run()
    apply_staging_authority_enrollment_namespace(db, environment="staging", enabled=True)
    apply_staging_two_human_ceremony_namespace(db, environment="staging", enabled=True)
    users = {1: _user(1, "actor-a"), 2: _user(2, "actor-b"), 3: _user(3, "actor-c", "tenant-a"), 4: _user(4, "actor-d", "tenant-b")}
    auth = FakeAuth(users)
    audit = AuditService(db)
    service = LocalTwoHumanStagingCeremony(db, auth=auth, mfa=FakeMFA(), audit=audit)
    return db, service


def _create(service):
    return service.create(_session(1, "session-a"), _release())


def _payload(db, ceremony_id, requester_key_id, reviewer_key_id, requester_subject="local-user:1", reviewer_subject="local-user:2"):
    with db.session() as connection:
        row = connection.execute("SELECT * FROM staging_two_human_ceremonies WHERE ceremony_id=?", (ceremony_id,)).fetchone()
    return {
        "artifact_version": "1", "authority_id": row["authority_id"],
        "operation": "staging_authority_enrollment",
        "purpose": "create_staging_bootstrap_authority", "environment": row["environment"],
        "control_tenant_id": row["control_tenant_id"],
        "database_target_identity": row["database_target_identity"],
        "application_commit": row["application_commit"], "repository_tree": row["repository_tree"],
        "image_digest": row["image_digest"], "requester_subject": requester_subject,
        "requester_key_id": requester_key_id, "reviewer_subject": reviewer_subject,
        "reviewer_key_id": reviewer_key_id, "approval_transaction_id": row["approval_transaction_id"],
        "nonce": row["nonce"], "issued_at": row["issued_at"], "expires_at": row["expires_at"],
    }


def _sign(payload, key):
    digest = hashlib.sha256(_canonical(payload, PAYLOAD_FIELDS)).digest()
    return base64.b64encode(key.sign(SIGNATURE_DOMAIN + b"\0" + digest)).decode()


def _approval_inputs(payload, requester_key, reviewer_key, *, bad_requester=False, bad_reviewer=False):
    requester_raw, reviewer_raw = _raw_public(requester_key), _raw_public(reviewer_key)
    return (
        {"key_id": "key-a", "public_key": base64.b64encode(requester_raw).decode(), "public_key_fingerprint": hashlib.sha256(requester_raw).hexdigest(), "signature": _sign(payload, requester_key) if not bad_requester else "A", "counterparty_subject": "local-user:2", "counterparty_key_id": "key-b"},
        {"key_id": "key-b", "public_key": base64.b64encode(reviewer_raw).decode(), "public_key_fingerprint": hashlib.sha256(reviewer_raw).hexdigest(), "signature": _sign(payload, reviewer_key) if not bad_reviewer else base64.b64encode(b"B" * 64).decode(), "counterparty_subject": "local-user:1", "counterparty_key_id": "key-a"},
    )


def test_two_distinct_mfa_sessions_finalize_to_offline_artifact(ceremony_fixture):
    db, service = ceremony_fixture
    created = _create(service)
    requester_key, reviewer_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    payload = _payload(db, created["ceremony_id"], "key-a", "key-b")
    requester, reviewer = _approval_inputs(payload, requester_key, reviewer_key)
    service.approve(created["ceremony_id"], "requester", _session(1, "session-a"), _release(), **requester)
    service.approve(created["ceremony_id"], "reviewer", _session(2, "session-b"), _release(), **reviewer)
    artifact = service.finalize(created["ceremony_id"], _session(2, "session-b"))
    assert verify_final_artifact(artifact)["verified"] is True
    assert artifact["payload"]["application_commit"] == EXPECTED_RELEASE["application_commit"]
    with pytest.raises(LocalTwoHumanCeremonyError, match="duplicate_finalization"):
        service.finalize(created["ceremony_id"], _session(2, "session-b"))
    tampered = dict(artifact, payload=dict(artifact["payload"], image_digest="sha256:" + "0" * 64))
    with pytest.raises(Exception):
        verify_final_artifact(tampered)
    evidence_tampered = dict(artifact, approval_evidence=[dict(item) for item in artifact["approval_evidence"]])
    evidence_tampered["approval_evidence"][0]["actor_id"] = "tampered"
    with pytest.raises(Exception):
        verify_final_artifact(evidence_tampered)
    metadata_tampered = dict(artifact, verification_metadata=dict(artifact["verification_metadata"]))
    metadata_tampered["verification_metadata"]["verifier"] = "tampered"
    with pytest.raises(Exception):
        verify_final_artifact(metadata_tampered)


@pytest.mark.parametrize("field", ["application_commit", "repository_tree", "image_digest", "database_target_identity", "environment"])
def test_release_confirmation_mismatch_rejected(ceremony_fixture, field):
    _db, service = ceremony_fixture
    confirmation = _release(); confirmation[field] = "wrong"
    with pytest.raises(LocalTwoHumanCeremonyError, match="release_confirmation_mismatch"):
        service.create(_session(1, "session-a"), confirmation)


@pytest.mark.parametrize("session", [_session(1, "session-a"), _session(2, "session-b")])
def test_missing_or_invalid_mfa_rejected(ceremony_fixture, session):
    db, service = ceremony_fixture
    service.mfa.valid = False
    with pytest.raises(LocalTwoHumanCeremonyError):
        service.create(session, _release())


def test_same_user_actor_credential_session_key_and_fingerprint_are_rejected(ceremony_fixture):
    db, service = ceremony_fixture
    created = _create(service)
    key = Ed25519PrivateKey.generate()
    raw = _raw_public(key)
    payload = _payload(db, created["ceremony_id"], "same-key", "other-key")
    values = {"key_id": "same-key", "public_key": base64.b64encode(raw).decode(), "public_key_fingerprint": hashlib.sha256(raw).hexdigest(), "signature": _sign(payload, key), "counterparty_subject": "local-user:2", "counterparty_key_id": "other-key"}
    service.approve(created["ceremony_id"], "requester", _session(1, "session-a"), _release(), **values)
    with pytest.raises(LocalTwoHumanCeremonyError):
        service.approve(created["ceremony_id"], "reviewer", _session(1, "session-a"), _release(), **values)


def test_wrong_role_and_missing_approval_block_finalization(ceremony_fixture):
    _db, service = ceremony_fixture
    created = _create(service)
    with pytest.raises(LocalTwoHumanCeremonyError, match="reviewer_role_denied"):
        service.approve(created["ceremony_id"], "reviewer", _session(1, "session-a"), _release(), key_id="k", public_key=base64.b64encode(b"0" * 32).decode(), public_key_fingerprint="0" * 64, signature="A" * 88)
    with pytest.raises(LocalTwoHumanCeremonyError, match="both_approvals_required"):
        service.finalize(created["ceremony_id"], _session(1, "session-a"))


def test_reviewer_cannot_approve_requester_role(ceremony_fixture):
    _db, service = ceremony_fixture
    created = _create(service)
    with pytest.raises(LocalTwoHumanCeremonyError, match="requester_role_denied"):
        service.approve(created["ceremony_id"], "requester", _session(2, "session-b"), _release(), key_id="k", public_key=base64.b64encode(b"0" * 32).decode(), public_key_fingerprint=hashlib.sha256(b"0" * 32).hexdigest(), signature=base64.b64encode(b"A" * 64).decode())


def test_expired_ceremony_rejected(ceremony_fixture):
    db, service = ceremony_fixture
    created = _create(service)
    with db.session() as connection:
        connection.execute("UPDATE staging_two_human_ceremonies SET expires_at=? WHERE ceremony_id=?", ("2000-01-01T00:00:00Z", created["ceremony_id"]))
    with pytest.raises(LocalTwoHumanCeremonyError, match="ceremony_expired"):
            service.approve(created["ceremony_id"], "requester", _session(1, "session-a"), _release(), key_id="k", public_key=base64.b64encode(b"0" * 32).decode(), public_key_fingerprint=hashlib.sha256(b"0" * 32).hexdigest(), signature=base64.b64encode(b"A" * 64).decode())
    with db.session() as connection:
        assert connection.execute("SELECT status FROM staging_two_human_ceremonies WHERE ceremony_id=?", (created["ceremony_id"],)).fetchone()["status"] == "EXPIRED"


def test_altered_or_bad_signature_fails_finalization(ceremony_fixture):
    db, service = ceremony_fixture
    created = _create(service)
    requester_key, reviewer_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    payload = _payload(db, created["ceremony_id"], "key-a", "key-b")
    requester, reviewer = _approval_inputs(payload, requester_key, reviewer_key, bad_reviewer=True)
    service.approve(created["ceremony_id"], "requester", _session(1, "session-a"), _release(), **requester)
    with pytest.raises(LocalTwoHumanCeremonyError, match="signature_verification_failed"):
        service.approve(created["ceremony_id"], "reviewer", _session(2, "session-b"), _release(), **reviewer)


def test_cancelled_and_duplicate_finalization_rejected(ceremony_fixture):
    _db, service = ceremony_fixture
    created = _create(service)
    service.cancel(created["ceremony_id"], _session(1, "session-a"))
    with pytest.raises(LocalTwoHumanCeremonyError):
        service.finalize(created["ceremony_id"], _session(1, "session-a"))
    assert not hasattr(service, "enroll")


def test_cross_tenant_creation_and_approval_and_finalization_fail_closed(ceremony_fixture):
    db, service = ceremony_fixture
    with pytest.raises(LocalTwoHumanCeremonyError, match="tenant_scope_mismatch"):
        service.create(_session(3, "tenant-a-session", "tenant-a"), _release(tenant="tenant-b"))
    created = _create(service)
    with pytest.raises(LocalTwoHumanCeremonyError, match="ceremony_not_found"):
        service.approve(created["ceremony_id"], "requester", _session(3, "tenant-a-session", "tenant-a"), _release(), key_id="k", public_key=base64.b64encode(b"0" * 32).decode(), public_key_fingerprint=hashlib.sha256(b"0" * 32).hexdigest(), signature=base64.b64encode(b"A" * 64).decode(), counterparty_subject="local-user:2", counterparty_key_id="key-b")
    with pytest.raises(LocalTwoHumanCeremonyError, match="ceremony_not_found"):
        service.finalize(created["ceremony_id"], _session(3, "tenant-a-session", "tenant-a"))

    tenant_b = service.create(_session(4, "tenant-b-requester", "tenant-b"), _release(tenant="tenant-b"))
    requester_key = Ed25519PrivateKey.generate()
    payload = _payload(db, tenant_b["ceremony_id"], "tenant-b-key", "tenant-a-key", "local-user:4", "local-user:3")
    raw = _raw_public(requester_key)
    requester = {
        "key_id": "tenant-b-key",
        "public_key": base64.b64encode(raw).decode(),
        "public_key_fingerprint": hashlib.sha256(raw).hexdigest(),
        "signature": _sign(payload, requester_key),
        "counterparty_subject": "local-user:3",
        "counterparty_key_id": "tenant-a-key",
    }
    service.approve(tenant_b["ceremony_id"], "requester", _session(4, "tenant-b-requester", "tenant-b"), _release(tenant="tenant-b"), **requester)
    with pytest.raises(LocalTwoHumanCeremonyError, match="ceremony_not_found"):
        service.approve(tenant_b["ceremony_id"], "reviewer", _session(3, "tenant-a-reviewer", "tenant-a"), _release(tenant="tenant-b"), key_id="tenant-a-key", public_key=base64.b64encode(b"1" * 32).decode(), public_key_fingerprint=hashlib.sha256(b"1" * 32).hexdigest(), signature=base64.b64encode(b"A" * 64).decode(), counterparty_subject="local-user:4", counterparty_key_id="tenant-b-key")
    with pytest.raises(LocalTwoHumanCeremonyError, match="ceremony_not_found"):
        service.finalize(tenant_b["ceremony_id"], _session(3, "tenant-a-finalizer", "tenant-a"))


def test_runtime_environment_guard_is_server_side(ceremony_fixture, monkeypatch):
    _db, service = ceremony_fixture
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    assert service.create(_session(1, "runtime-staging"), _release())["status"] == "REQUESTED"
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    with pytest.raises(LocalTwoHumanCeremonyError, match="staging_runtime_required"):
        service.create(_session(1, "runtime-production"), _release())
    with pytest.raises(LocalTwoHumanCeremonyError, match="staging_runtime_required"):
        service.create(_session(1, "runtime-production-2"), dict(_release(), environment="production"))
    monkeypatch.delenv("SENTINEL_DNA_ENV", raising=False)
    with pytest.raises(LocalTwoHumanCeremonyError, match="staging_runtime_required"):
        service.create(_session(1, "runtime-missing"), _release())


@pytest.mark.parametrize("runtime", ["production", "development", "testing", "test", "unknown", ""])
def test_migration_014_direct_invocation_refuses_non_staging(tmp_path, monkeypatch, runtime):
    migration_013 = importlib.import_module("database.migrations.013_local_two_human_staging_ceremony")
    migration_014 = importlib.import_module("database.migrations.014_local_two_human_approval_binding")
    db = DatabaseConnection(tmp_path / ("migration-" + (runtime or "missing") + ".sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    with db.session() as connection:
        migration_013.upgrade(connection)
    monkeypatch.setenv("SENTINEL_DNA_ENV", runtime)
    with db.session() as connection:
        with pytest.raises(RuntimeError, match="requires_staging"):
            migration_014.upgrade(connection)


def test_migration_014_direct_invocation_allows_explicit_staging(tmp_path, monkeypatch):
    migration_013 = importlib.import_module("database.migrations.013_local_two_human_staging_ceremony")
    migration_014 = importlib.import_module("database.migrations.014_local_two_human_approval_binding")
    db = DatabaseConnection(tmp_path / "migration-staging.sqlite")
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    with db.session() as connection:
        migration_013.upgrade(connection)
        migration_014.upgrade(connection)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(staging_two_human_approvals)").fetchall()}
    assert {"counterparty_subject", "counterparty_key_id", "signed_payload_hash"} <= columns
