import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from database.backend import SQLiteBackend
from database.migration_runner import MigrationRunner
from database.migrations.registry import apply_staging_authority_enrollment_namespace
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.staging_authority_enrollment import (
    PAYLOAD_FIELDS,
    SIGNATURE_DOMAIN,
    StagingAuthorityArtifactVerifier,
    StagingAuthorityEnrollmentService,
    StagingAuthoritySignatureProvider,
    StagingAuthorityVerificationError,
    StagingTrustManifest,
)
from services.auth.staging_bootstrap_authorization import VerifiedBootstrapPrincipal
from services.identity.authentication import CanonicalAuthenticationBoundary
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService


def _public_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    monkeypatch.setenv("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "disposable_staging")
    db_path = tmp_path / "authority.sqlite"
    backend = SQLiteBackend(db_path)
    MigrationRunner(backend).run()
    assert apply_staging_authority_enrollment_namespace(
        backend, environment="staging", enabled=True
    ) == (12,)
    db = backend
    requester = Ed25519PrivateKey.generate()
    reviewer = Ed25519PrivateKey.generate()
    requester_public = _public_bytes(requester)
    reviewer_public = _public_bytes(reviewer)
    payload = {
        "artifact_version": "1",
        "authority_id": "authority-test-1",
        "operation": "staging_authority_enrollment",
        "purpose": "create_staging_bootstrap_authority",
        "environment": "staging",
        "control_tenant_id": "staging-control-test",
        "database_target_identity": "postgresql://sentinel@rehearsal:5432/sentinel_dna",
        "application_commit": "a" * 40,
        "repository_tree": "b" * 40,
        "image_digest": "sha256:" + "c" * 64,
        "requester_subject": "requester-subject",
        "requester_key_id": "requester-key-1",
        "reviewer_subject": "reviewer-subject",
        "reviewer_key_id": "reviewer-key-1",
        "approval_transaction_id": "transaction-test-1",
        "nonce": "nonce-test-1",
        "issued_at": "2026-09-23T10:00:00Z",
        "expires_at": "2030-09-23T10:00:00Z",
    }
    unsigned_manifest = {
        "authority_id": payload["authority_id"],
        "environment": "staging",
        "requester_key_id": payload["requester_key_id"],
        "requester_public_key_fingerprint": hashlib.sha256(requester_public).hexdigest(),
        "reviewer_key_id": payload["reviewer_key_id"],
        "reviewer_public_key_fingerprint": hashlib.sha256(reviewer_public).hexdigest(),
        "allowed_database_target_identity": payload["database_target_identity"],
        "allowed_application_commit": payload["application_commit"],
        "allowed_repository_tree": payload["repository_tree"],
        "allowed_image_digest": payload["image_digest"],
        "manifest_version": "1",
        "manifest_expiry": "2030-01-01T00:00:00Z",
        "authority_status": "active",
        "requester_key_status": "active",
        "reviewer_key_status": "active",
    }
    manifest_bytes = json.dumps(dict(sorted(unsigned_manifest.items())), separators=(",", ":"), ensure_ascii=False).encode()
    manifest = dict(unsigned_manifest, manifest_digest=hashlib.sha256(manifest_bytes).hexdigest())
    payload_bytes = json.dumps(dict(sorted(payload.items())), separators=(",", ":"), ensure_ascii=False).encode()
    artifact_hash = hashlib.sha256(payload_bytes).hexdigest()
    message = SIGNATURE_DOMAIN + b"\0" + bytes.fromhex(artifact_hash)
    envelope = {
        "payload": payload,
        "requester_signature": base64.b64encode(requester.sign(message)).decode(),
        "reviewer_signature": base64.b64encode(reviewer.sign(message)).decode(),
    }
    resolver = {
        payload["requester_key_id"]: requester_public,
        payload["reviewer_key_id"]: reviewer_public,
    }
    return db, payload, manifest, envelope, resolver


def test_verifier_accepts_valid_pinned_dual_signature(tmp_path, monkeypatch):
    db, _payload, manifest, envelope, resolver = _fixture(tmp_path, monkeypatch)
    ceremony = StagingAuthorityArtifactVerifier().verify(envelope, manifest, resolver)
    assert ceremony.artifact_hash == hashlib.sha256(
        json.dumps(dict(sorted(envelope["payload"].items())), separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert db is not None


def test_verifier_rejects_duplicate_unknown_and_altered_fields(tmp_path, monkeypatch):
    _db, payload, manifest, envelope, resolver = _fixture(tmp_path, monkeypatch)
    altered = dict(envelope, payload=dict(payload, database_target_identity="postgresql://other@rehearsal:5432/sentinel_dna"))
    with pytest.raises(StagingAuthorityVerificationError):
        StagingAuthorityArtifactVerifier().verify(altered, manifest, resolver)
    with pytest.raises(StagingAuthorityVerificationError):
        StagingAuthorityArtifactVerifier().verify(dict(envelope, extra="x"), manifest, resolver)
    duplicate = '{"payload":' + json.dumps(payload) + ',"payload":' + json.dumps(payload) + ',"requester_signature":"x","reviewer_signature":"x"}'
    with pytest.raises(StagingAuthorityVerificationError, match="duplicate"):
        StagingAuthorityArtifactVerifier().verify(duplicate, manifest, resolver)


def test_enrollment_is_provider_only_and_canonical(tmp_path, monkeypatch):
    db, payload, manifest, envelope, resolver = _fixture(tmp_path, monkeypatch)
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    result = StagingAuthorityEnrollmentService(
        db, auth=auth, authority=authority, audit=AuditService(db)
    ).enroll(StagingAuthorityArtifactVerifier().verify(envelope, manifest, resolver))
    requester = auth.get_by_id(result["requester_user_id"])
    reviewer = auth.get_by_id(result["reviewer_user_id"])
    assert requester.password_hash is None and not requester.password_authentication_enabled
    assert reviewer.password_hash is None and not reviewer.password_authentication_enabled
    assert auth.authenticate(requester.username, "any-password-long-enough") is None
    assert authority.resolve(payload["control_tenant_id"], result["reviewer_actor_id"])[2].role == "staging_bootstrap_reviewer"
    provider = StagingAuthoritySignatureProvider(StagingAuthorityArtifactVerifier(), db=db, authority=authority)
    principal = provider.authenticate({"envelope": envelope, "manifest": manifest, "key_resolver": resolver, "principal": "reviewer"})
    assert auth.authenticate_provider(
        principal.provider, principal.subject,
        authentication_method=principal.authentication_method,
        credential_id=principal.credential_id,
    ) is not None
    auth.create_persistent_session(
        reviewer, "raw-disposable-token", payload["control_tenant_id"],
        "session-disposable", "2030-09-23T10:00:00+00:00",
        auth_method=principal.authentication_method,
    )
    with db.session() as connection:
        assert connection.execute("SELECT auth_method FROM persistent_sessions WHERE id=?", ("session-disposable",)).fetchone()["auth_method"] == "staging_authority_signature"
    verified = VerifiedBootstrapPrincipal.from_provider_principal(
        principal,
        boundary=CanonicalAuthenticationBoundary(CanonicalRequestContextService(authority)),
        db=db,
    )
    assert verified.actor_id == result["reviewer_actor_id"]
    auth.deactivate_user(reviewer.id)
    assert auth.authenticate_provider(
        principal.provider, principal.subject,
        authentication_method=principal.authentication_method,
        credential_id=principal.credential_id,
    ) is None
    with db.session() as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM staging_authority_enrollments").fetchone()
        audit = connection.execute("SELECT details_json FROM audit_events").fetchall()
    assert row["count"] == 1
    assert "private" not in json.dumps([dict(item) for item in audit]).lower()


def test_enrollment_rolls_back_on_duplicate_binding(tmp_path, monkeypatch):
    db, _payload, manifest, envelope, resolver = _fixture(tmp_path, monkeypatch)
    ceremony = StagingAuthorityArtifactVerifier().verify(envelope, manifest, resolver)
    service = StagingAuthorityEnrollmentService(db, auth=AuthService(db), authority=CanonicalAuthorityService(db), audit=AuditService(db))
    service.enroll(ceremony)
    with pytest.raises(StagingAuthorityVerificationError, match="authority_already_enrolled"):
        service.enroll(ceremony)
    with db.session() as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM staging_authority_enrollments").fetchone()["count"] == 1


def test_migration_012_is_rejected_outside_staging(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "production")
    backend = SQLiteBackend(tmp_path / "blocked.sqlite")
    MigrationRunner(backend).run()
    with pytest.raises(RuntimeError, match="requires_staging"):
        apply_staging_authority_enrollment_namespace(backend, environment="staging", enabled=True)
