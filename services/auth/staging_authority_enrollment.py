"""Purely verifiable, staging-only first-authority enrollment."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from database.canonical_authority import (
    CanonicalIdentityBindingRepository,
    ProviderTenantTrustRepository,
    CanonicalUnitOfWork,
)
from database.connection import DatabaseConnection, database
from services.audit.service import AuditService
from services.identity.authentication import AuthenticatedProviderPrincipal
from services.identity.canonical_authority import CanonicalAuthorityService


PROVIDER = "sentinel-staging-authority-v1"
AUTHENTICATION_METHOD = "staging_authority_signature"
SIGNATURE_DOMAIN = b"sentinel-dna/staging-authority-enrollment/v1"
PAYLOAD_FIELDS = frozenset({
    "artifact_version", "authority_id", "operation", "purpose", "environment",
    "control_tenant_id", "database_target_identity", "application_commit",
    "repository_tree", "image_digest", "requester_subject", "requester_key_id",
    "reviewer_subject", "reviewer_key_id", "approval_transaction_id", "nonce",
    "issued_at", "expires_at",
})
ENVELOPE_FIELDS = frozenset({"payload", "requester_signature", "reviewer_signature"})
MANIFEST_FIELDS = frozenset({
    "authority_id", "environment", "requester_key_id",
    "requester_public_key_fingerprint", "reviewer_key_id",
    "reviewer_public_key_fingerprint", "allowed_database_target_identity",
    "allowed_application_commit", "allowed_repository_tree", "allowed_image_digest",
    "manifest_version", "manifest_expiry", "manifest_digest", "authority_status",
    "requester_key_status", "reviewer_key_status",
})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40_64 = re.compile(r"^[0-9a-f]{40,64}$")
IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")


class StagingAuthorityVerificationError(ValueError):
    pass


def _duplicate_reject(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StagingAuthorityVerificationError("duplicate_semantic_field")
        result[key] = value
    return result


def _json_object(value: str | bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(value, object_pairs_hook=_duplicate_reject)
    except StagingAuthorityVerificationError:
        raise
    except Exception as exc:
        raise StagingAuthorityVerificationError("invalid_json") from exc
    if not isinstance(parsed, dict):
        raise StagingAuthorityVerificationError("json_object_required")
    return parsed


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise StagingAuthorityVerificationError(f"invalid_{field}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise StagingAuthorityVerificationError(f"invalid_{field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise StagingAuthorityVerificationError(f"invalid_{field}")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Mapping[str, Any], expected: frozenset[str]) -> bytes:
    if set(value) != expected:
        raise StagingAuthorityVerificationError("payload_fields_invalid")
    if any(isinstance(item, (float, list, tuple)) for item in value.values()):
        raise StagingAuthorityVerificationError("payload_value_type_invalid")
    try:
        return json.dumps(dict(sorted(value.items())), ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StagingAuthorityVerificationError("payload_not_canonicalizable") from exc


def _digest(value: Mapping[str, Any], expected: frozenset[str]) -> str:
    return hashlib.sha256(_canonical(value, expected)).hexdigest()


def _decode_signature(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise StagingAuthorityVerificationError("signature_required")
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise StagingAuthorityVerificationError("signature_invalid") from exc
    if len(decoded) != 64:
        raise StagingAuthorityVerificationError("signature_invalid")
    return decoded


def _public_key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        try:
            value = base64.b64decode(value, validate=True)
        except Exception as exc:
            raise StagingAuthorityVerificationError("public_key_invalid") from exc
    if not isinstance(value, bytes) or len(value) != 32:
        raise StagingAuthorityVerificationError("public_key_invalid")
    return value


def _target_is_staging(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme in {"postgres", "postgresql"}
        and parsed.username in {"sentinel", "sentinel_rehearsal"}
        and parsed.password is None
        and parsed.hostname in {"postgres", "rehearsal", "127.0.0.1"}
        and ((parsed.hostname in {"postgres", "rehearsal"} and parsed.path == "/sentinel_dna") or
             (parsed.hostname == "127.0.0.1" and parsed.path == "/sentinel_dna_rehearsal"))
        and not parsed.query and not parsed.fragment
    )


@dataclass(frozen=True)
class StagingTrustManifest:
    authority_id: str
    environment: str
    requester_key_id: str
    requester_public_key_fingerprint: str
    reviewer_key_id: str
    reviewer_public_key_fingerprint: str
    allowed_database_target_identity: str
    allowed_application_commit: str
    allowed_repository_tree: str
    allowed_image_digest: str
    manifest_version: str
    manifest_expiry: str
    manifest_digest: str
    authority_status: str
    requester_key_status: str
    reviewer_key_status: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StagingTrustManifest":
        if set(value) != MANIFEST_FIELDS:
            raise StagingAuthorityVerificationError("manifest_fields_invalid")
        manifest = cls(**{field: value[field] for field in MANIFEST_FIELDS})
        if manifest.environment != "staging" or manifest.authority_status != "active":
            raise StagingAuthorityVerificationError("manifest_scope_invalid")
        if manifest.requester_key_status != "active" or manifest.reviewer_key_status != "active":
            raise StagingAuthorityVerificationError("manifest_key_revoked")
        if not HEX64.fullmatch(manifest.requester_public_key_fingerprint) or not HEX64.fullmatch(manifest.reviewer_public_key_fingerprint):
            raise StagingAuthorityVerificationError("manifest_fingerprint_invalid")
        if not HEX64.fullmatch(manifest.manifest_digest):
            raise StagingAuthorityVerificationError("manifest_digest_invalid")
        unsigned = dict(value)
        unsigned.pop("manifest_digest")
        if hashlib.sha256(_canonical(unsigned, MANIFEST_FIELDS - {"manifest_digest"})).hexdigest() != manifest.manifest_digest:
            raise StagingAuthorityVerificationError("manifest_digest_mismatch")
        if _utc(manifest.manifest_expiry, "manifest_expiry") <= datetime.now(timezone.utc):
            raise StagingAuthorityVerificationError("manifest_expired")
        if not _target_is_staging(manifest.allowed_database_target_identity):
            raise StagingAuthorityVerificationError("manifest_database_target_invalid")
        if not HEX40_64.fullmatch(manifest.allowed_application_commit) or not HEX40_64.fullmatch(manifest.allowed_repository_tree):
            raise StagingAuthorityVerificationError("manifest_revision_invalid")
        if not IMAGE_DIGEST.fullmatch(manifest.allowed_image_digest):
            raise StagingAuthorityVerificationError("manifest_image_invalid")
        return manifest


@dataclass(frozen=True)
class VerifiedStagingAuthorityCeremony:
    payload: Mapping[str, str]
    artifact_hash: str
    requester_public_key: bytes
    reviewer_public_key: bytes
    manifest: StagingTrustManifest

    @property
    def requester_key_fingerprint(self) -> str:
        return hashlib.sha256(self.requester_public_key).hexdigest()

    @property
    def reviewer_key_fingerprint(self) -> str:
        return hashlib.sha256(self.reviewer_public_key).hexdigest()


class StagingAuthorityArtifactVerifier:
    """Pure verifier: it never opens or mutates the application database."""

    def verify(
        self,
        envelope: Mapping[str, Any] | str | bytes,
        manifest: StagingTrustManifest | Mapping[str, Any],
        key_resolver: Mapping[str, bytes | str],
    ) -> VerifiedStagingAuthorityCeremony:
        if isinstance(envelope, (str, bytes)):
            envelope = _json_object(envelope)
        if not isinstance(envelope, Mapping) or set(envelope) != ENVELOPE_FIELDS:
            raise StagingAuthorityVerificationError("envelope_fields_invalid")
        payload = envelope["payload"]
        if isinstance(payload, (str, bytes)):
            payload = _json_object(payload)
        if not isinstance(payload, Mapping) or set(payload) != PAYLOAD_FIELDS:
            raise StagingAuthorityVerificationError("payload_fields_invalid")
        if isinstance(manifest, (str, bytes)):
            manifest = _json_object(manifest)
        if not isinstance(manifest, StagingTrustManifest):
            manifest = StagingTrustManifest.from_mapping(manifest)
        if payload["environment"] != "staging" or not _target_is_staging(str(payload["database_target_identity"])):
            raise StagingAuthorityVerificationError("staging_scope_invalid")
        if payload["authority_id"] != manifest.authority_id or payload["requester_key_id"] != manifest.requester_key_id or payload["reviewer_key_id"] != manifest.reviewer_key_id:
            raise StagingAuthorityVerificationError("manifest_binding_mismatch")
        if payload["database_target_identity"] != manifest.allowed_database_target_identity:
            raise StagingAuthorityVerificationError("database_target_mismatch")
        if payload["application_commit"] != manifest.allowed_application_commit or payload["repository_tree"] != manifest.allowed_repository_tree or payload["image_digest"] != manifest.allowed_image_digest:
            raise StagingAuthorityVerificationError("release_binding_mismatch")
        for field in ("authority_id", "requester_key_id", "reviewer_key_id"):
            lowered = str(payload[field]).lower()
            if any(marker in lowered for marker in ("tls", "ca", "private", "certificate", "secret")):
                raise StagingAuthorityVerificationError("key_reference_forbidden")
        if not all(isinstance(payload[field], str) and SAFE_ID.fullmatch(payload[field]) for field in PAYLOAD_FIELDS - {"issued_at", "expires_at", "image_digest", "application_commit", "repository_tree", "database_target_identity"}):
            raise StagingAuthorityVerificationError("payload_identifier_invalid")
        if payload["application_commit"] != payload["application_commit"].lower() or payload["repository_tree"] != payload["repository_tree"].lower() or not IMAGE_DIGEST.fullmatch(payload["image_digest"]):
            raise StagingAuthorityVerificationError("payload_digest_invalid")
        issued = _utc(payload["issued_at"], "issued_at")
        expires = _utc(payload["expires_at"], "expires_at")
        now = datetime.now(timezone.utc)
        if expires <= issued or expires <= now:
            raise StagingAuthorityVerificationError("artifact_expired")
        if issued > now:
            raise StagingAuthorityVerificationError("artifact_from_future")
        if payload["requester_key_id"] == payload["reviewer_key_id"]:
            raise StagingAuthorityVerificationError("identical_keys")
        try:
            requester_key = _public_key(key_resolver[payload["requester_key_id"]])
            reviewer_key = _public_key(key_resolver[payload["reviewer_key_id"]])
        except KeyError as exc:
            raise StagingAuthorityVerificationError("pinned_key_not_found") from exc
        if hashlib.sha256(requester_key).hexdigest() != manifest.requester_public_key_fingerprint or hashlib.sha256(reviewer_key).hexdigest() != manifest.reviewer_public_key_fingerprint:
            raise StagingAuthorityVerificationError("fingerprint_mismatch")
        if requester_key == reviewer_key:
            raise StagingAuthorityVerificationError("identical_keys")
        artifact_hash = _digest(payload, PAYLOAD_FIELDS)
        message = SIGNATURE_DOMAIN + b"\0" + bytes.fromhex(artifact_hash)
        for key, signature in ((requester_key, envelope["requester_signature"]), (reviewer_key, envelope["reviewer_signature"])):
            try:
                Ed25519PublicKey.from_public_bytes(key).verify(_decode_signature(signature), message)
            except Exception as exc:
                raise StagingAuthorityVerificationError("signature_verification_failed") from exc
        return VerifiedStagingAuthorityCeremony(dict(payload), artifact_hash, requester_key, reviewer_key, manifest)


class StagingAuthorityEnrollmentService:
    """Atomically enroll two provider-only canonical staging principals."""

    def __init__(self, db: DatabaseConnection = database, *, auth=None, authority=None, audit=None):
        self.db = db
        self.auth = auth
        self.authority = authority or CanonicalAuthorityService(db)
        self.audit = audit or AuditService(db)

    def enroll(self, ceremony: VerifiedStagingAuthorityCeremony) -> dict[str, Any]:
        payload = ceremony.payload
        if payload["operation"] != "staging_authority_enrollment" or payload["purpose"] != "create_staging_bootstrap_authority":
            raise StagingAuthorityVerificationError("enrollment_operation_invalid")
        auth = self.auth
        if auth is None:
            from .auth_service import AuthService
            auth = AuthService(self.db)
        enrollment_id = str(uuid4())
        provider = PROVIDER
        issuer = PROVIDER
        with CanonicalUnitOfWork(self.db) as unit:
            existing = unit.conn.execute(
                "SELECT 1 FROM staging_authority_enrollments WHERE authority_id=? AND status='ENROLLED'",
                (payload["authority_id"],),
            ).fetchone()
            if existing:
                raise StagingAuthorityVerificationError("authority_already_enrolled")
            tenant = self.authority.tenants.get(payload["control_tenant_id"], connection=unit.conn)
            if tenant is None:
                tenant = self.authority.tenants.create("Sentinel DNA staging control tenant", payload["control_tenant_id"], connection=unit.conn)
            elif tenant.status != "active":
                raise StagingAuthorityVerificationError("control_tenant_inactive")
            requester_actor = "staging-authority:" + hashlib.sha256((payload["authority_id"] + ":requester").encode()).hexdigest()[:32]
            reviewer_actor = "staging-authority:" + hashlib.sha256((payload["authority_id"] + ":reviewer").encode()).hexdigest()[:32]
            if requester_actor == reviewer_actor or payload["requester_subject"] == payload["reviewer_subject"]:
                raise StagingAuthorityVerificationError("principals_not_distinct")
            requester_email = requester_actor.replace(":", ".") + "@staging-authority.invalid"
            reviewer_email = reviewer_actor.replace(":", ".") + "@staging-authority.invalid"
            self.authority.identities.create(requester_email, "staging bootstrap requester", requester_actor, connection=unit.conn)
            self.authority.identities.create(reviewer_email, "staging bootstrap reviewer", reviewer_actor, connection=unit.conn)
            self.authority.memberships.add(payload["control_tenant_id"], requester_actor, "staging_bootstrap_reviewer", connection=unit.conn)
            self.authority.memberships.add(payload["control_tenant_id"], reviewer_actor, "staging_bootstrap_reviewer", connection=unit.conn)
            requester = auth.register_provider_only(
                "staging-requester-" + payload["requester_key_id"][:16], requester_email, provider,
                payload["requester_subject"], tenant_id=payload["control_tenant_id"], actor_id=requester_actor,
                credential_id=payload["requester_key_id"], connection=unit.conn,
            )
            reviewer = auth.register_provider_only(
                "staging-reviewer-" + payload["reviewer_key_id"][:16], reviewer_email, provider,
                payload["reviewer_subject"], tenant_id=payload["control_tenant_id"], actor_id=reviewer_actor,
                credential_id=payload["reviewer_key_id"], connection=unit.conn,
            )
            ProviderTenantTrustRepository(unit.conn).create(provider, issuer, payload["authority_id"], payload["control_tenant_id"], "staging-authority-enrollment")
            bindings = CanonicalIdentityBindingRepository(unit.conn)
            bindings.create(provider, payload["requester_subject"], requester_actor, "staging-authority-enrollment")
            bindings.create(provider, payload["reviewer_subject"], reviewer_actor, "staging-authority-enrollment")
            unit.conn.execute(
                """INSERT INTO staging_authority_enrollments(
                   enrollment_id,authority_id,nonce,enrollment_transaction_id,artifact_hash,
                   control_tenant_id,requester_subject,requester_key_id,reviewer_subject,reviewer_key_id,
                   requester_fingerprint,reviewer_fingerprint,environment,database_target_identity,
                   application_commit,repository_tree,image_digest,issued_at,expires_at,status,
                   requester_actor_id,reviewer_actor_id,requester_user_id,reviewer_user_id,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (enrollment_id, payload["authority_id"], payload["nonce"], payload["approval_transaction_id"], ceremony.artifact_hash,
                 payload["control_tenant_id"], payload["requester_subject"], payload["requester_key_id"], payload["reviewer_subject"], payload["reviewer_key_id"],
                 ceremony.requester_key_fingerprint, ceremony.reviewer_key_fingerprint, payload["environment"], payload["database_target_identity"],
                 payload["application_commit"], payload["repository_tree"], payload["image_digest"], payload["issued_at"], payload["expires_at"], "ENROLLED",
                 requester_actor, reviewer_actor, requester.id, reviewer.id, datetime.now(timezone.utc).isoformat()),
            )
            self.audit.record("STAGING_AUTHORITY_ENROLLED", tenant_id=payload["control_tenant_id"], actor_id=reviewer_actor, operation=payload["operation"], outcome="success", metadata={"enrollment_id": enrollment_id, "authority_id": payload["authority_id"], "artifact_hash": ceremony.artifact_hash, "requester_key_id": payload["requester_key_id"], "reviewer_key_id": payload["reviewer_key_id"]}, connection=unit.conn)
            return {"enrollment_id": enrollment_id, "tenant_id": payload["control_tenant_id"], "requester_actor_id": requester_actor, "reviewer_actor_id": reviewer_actor, "requester_user_id": requester.id, "reviewer_user_id": reviewer.id, "artifact_hash": ceremony.artifact_hash}


class StagingAuthoritySignatureProvider:
    """Provider adapter that verifies the ceremony before canonical binding lookup."""

    def __init__(self, verifier: StagingAuthorityArtifactVerifier, *, db: DatabaseConnection = database, authority=None):
        self.verifier, self.db = verifier, db
        self.authority = authority or CanonicalAuthorityService(db)

    def authenticate(self, request: Mapping[str, Any]) -> AuthenticatedProviderPrincipal:
        ceremony = self.verifier.verify(request["envelope"], request["manifest"], request["key_resolver"])
        side = request.get("principal")
        if side not in {"requester", "reviewer"}:
            raise StagingAuthorityVerificationError("principal_side_required")
        subject = ceremony.payload[f"{side}_subject"]
        key_id = ceremony.payload[f"{side}_key_id"]
        with self.db.session() as connection:
            trust = connection.execute(
                """SELECT 1 FROM canonical_provider_tenant_trusts
                   WHERE provider=? AND issuer=? AND external_tenant_id=?
                     AND canonical_tenant_id=? AND status='active'""",
                (PROVIDER, PROVIDER, ceremony.payload["authority_id"], ceremony.payload["control_tenant_id"]),
            ).fetchone()
            if not trust:
                raise StagingAuthorityVerificationError("provider_tenant_trust_denied")
            binding = connection.execute("SELECT actor_id FROM canonical_identity_bindings WHERE provider=? AND external_subject=? AND status='active'", (PROVIDER, subject)).fetchone()
            if not binding:
                raise StagingAuthorityVerificationError("identity_binding_denied")
            actor_id = binding["actor_id"]
            self.authority.resolve(ceremony.payload["control_tenant_id"], actor_id, connection=connection)
        fingerprint = ceremony.requester_key_fingerprint if side == "requester" else ceremony.reviewer_key_fingerprint
        return AuthenticatedProviderPrincipal(PROVIDER, subject, ceremony.payload["control_tenant_id"], actor_id, AUTHENTICATION_METHOD, key_id, external_subject=subject, key_id=key_id, key_fingerprint=fingerprint)


__all__ = [
    "AUTHENTICATION_METHOD", "PAYLOAD_FIELDS", "PROVIDER", "SIGNATURE_DOMAIN",
    "StagingAuthorityArtifactVerifier", "StagingAuthorityEnrollmentService",
    "StagingAuthoritySignatureProvider", "StagingAuthorityVerificationError",
    "StagingTrustManifest", "VerifiedStagingAuthorityCeremony",
]
