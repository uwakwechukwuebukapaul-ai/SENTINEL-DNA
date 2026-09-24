"""Fail-closed local two-human staging authority ceremony coordinator."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import secrets
from typing import Any, Mapping
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, session

from database.connection import DatabaseConnection, database
from services.auth.mfa import MFAService
from services.auth.staging_authority_enrollment import (
    MANIFEST_FIELDS,
    PAYLOAD_FIELDS,
    SIGNATURE_DOMAIN,
    StagingAuthorityArtifactVerifier,
    StagingAuthorityVerificationError,
    _canonical,
    _digest,
    _public_key,
)
from services.audit.service import AuditService


CEREMONY_STATES = frozenset({
    "REQUESTED", "REQUESTER_APPROVED", "REVIEWER_APPROVED", "FINALIZED",
    "EXPIRED", "CANCELLED",
})
ACTIVE_STATES = frozenset({"REQUESTED", "REQUESTER_APPROVED", "REVIEWER_APPROVED"})
EXPECTED_RELEASE = {
    "application_commit": "c5e7e789ef4f99394218612f8585fd115f32beba",
    "repository_tree": "252db5689e4fce6fe2cb1094c1efd73711b54a19",
    "image_digest": "sha256:a759b179796650c33f6522423d14f16e80b4c9f7d7c08bd764c2c48bc38a8a6c",
    "environment": "staging",
    "database_target_identity": "postgresql://sentinel@postgres:5432/sentinel_dna",
}
PROVIDER = "sentinel-local-human-mfa-v1"
CEREMONY_TTL = timedelta(minutes=30)
APPROVAL_BINDING_FIELDS = frozenset({"ceremony_id", "approval_evidence", "verification_metadata", "artifact_hash"})


class LocalTwoHumanCeremonyError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LocalTwoHumanCeremonyError("timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LocalTwoHumanCeremonyError("timestamp_invalid") from exc
    return parsed.astimezone(timezone.utc)


def _session_reference_hash(token: str, ceremony_id: str) -> str:
    if not token:
        raise LocalTwoHumanCeremonyError("mfa_session_required")
    return hashlib.sha256(
        ("sentinel-dna/local-two-human-session/v1\0" + ceremony_id + "\0" + token).encode()
    ).hexdigest()


def _release_confirmation(value: Mapping[str, Any]) -> dict[str, str]:
    expected = set(EXPECTED_RELEASE) | {"authority_id", "control_tenant_id"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise LocalTwoHumanCeremonyError("release_confirmation_fields_invalid")
    normalized = {key: str(value[key]) for key in expected}
    if any(not normalized[key] for key in expected):
        raise LocalTwoHumanCeremonyError("release_confirmation_required")
    if any(normalized[key] != EXPECTED_RELEASE[key] for key in EXPECTED_RELEASE):
        raise LocalTwoHumanCeremonyError("release_confirmation_mismatch")
    return normalized


def _public_key_material(public_key: Any, fingerprint: str) -> tuple[str, str]:
    if not isinstance(public_key, str) or not public_key:
        raise LocalTwoHumanCeremonyError("public_key_required")
    try:
        raw = _public_key(public_key)
    except Exception as exc:
        raise LocalTwoHumanCeremonyError("public_key_invalid") from exc
    calculated = hashlib.sha256(raw).hexdigest()
    if not isinstance(fingerprint, str) or not hmac.compare_digest(calculated, fingerprint):
        raise LocalTwoHumanCeremonyError("public_key_fingerprint_mismatch")
    return base64.b64encode(raw).decode("ascii"), calculated


def _signature_shape(signature: Any) -> str:
    if not isinstance(signature, str) or not signature:
        raise LocalTwoHumanCeremonyError("signature_required")
    try:
        raw = base64.b64decode(signature, validate=True)
    except Exception as exc:
        raise LocalTwoHumanCeremonyError("signature_invalid") from exc
    if len(raw) != 64:
        raise LocalTwoHumanCeremonyError("signature_invalid")
    return signature


@dataclass(frozen=True)
class AuthenticatedHuman:
    user_id: int
    actor_id: str
    provider_subject: str
    credential_id: str
    mfa_session_hash: str
    tenant_id: str


class LocalTwoHumanStagingCeremony:
    """Coordinates human/session separation and delegates crypto to the existing verifier."""

    def __init__(self, db: DatabaseConnection = database, *, auth, mfa: MFAService, audit: AuditService, authority=None):
        self.db = db
        self.auth = auth
        self.mfa = mfa
        self.audit = audit
        self.authority = authority

    def _authenticated_human(self, flask_session: Mapping[str, Any], ceremony_id: str) -> AuthenticatedHuman:
        user_id = flask_session.get("user_id")
        session_version = flask_session.get("session_version")
        tenant_id = flask_session.get("organization_id")
        user = self.auth.session_user(user_id, session_version)
        if user is None or not bool(getattr(user, "mfa_required", False)):
            raise LocalTwoHumanCeremonyError("authenticated_mfa_account_required")
        token = flask_session.get("mfa_session_token")
        if not self.mfa.session_verified(user.id, token, session_version=session_version, tenant_id=tenant_id):
            raise LocalTwoHumanCeremonyError("mfa_session_invalid")
        actor_id = str(user.actor_id or "").strip()
        if not actor_id or not tenant_id:
            raise LocalTwoHumanCeremonyError("canonical_identity_required")
        if getattr(user, "tenant_id", tenant_id) != tenant_id:
            raise LocalTwoHumanCeremonyError("tenant_scope_mismatch")
        if self.authority is not None:
            membership = self.authority.memberships.get(tenant_id, actor_id)
            if membership is None or membership.status != "active":
                raise LocalTwoHumanCeremonyError("canonical_membership_required")
        # Password/TOTP accounts have no external provider subject. Use the
        # stable local account principal explicitly; provider-bound accounts
        # may replace this with their active external subject in a later adapter.
        provider_subject = f"local-user:{int(user.id)}"
        credential_id = f"local-account:{int(user.id)}"
        return AuthenticatedHuman(
            user_id=int(user.id),
            actor_id=actor_id,
            provider_subject=provider_subject,
            credential_id=credential_id,
            mfa_session_hash=_session_reference_hash(str(token), ceremony_id),
            tenant_id=str(tenant_id),
        )

    @staticmethod
    def _runtime_environment() -> str:
        try:
            configured = current_app.config.get("ENVIRONMENT")
        except RuntimeError:
            configured = os.getenv("SENTINEL_DNA_ENV", "")
        return str(configured or "").strip().lower()

    def _require_staging_runtime(self) -> None:
        if self._runtime_environment() != "staging":
            raise LocalTwoHumanCeremonyError("staging_runtime_required")

    def _get(self, ceremony_id: str, *, connection=None):
        owned = connection or self.db.session()
        with owned as conn:
            row = conn.execute(
                "SELECT * FROM staging_two_human_ceremonies WHERE ceremony_id=?",
                (str(ceremony_id),),
            ).fetchone()
        if not row:
            raise LocalTwoHumanCeremonyError("ceremony_not_found")
        return row

    @staticmethod
    def _ensure_active(connection, row, now: datetime) -> None:
        if row["status"] not in ACTIVE_STATES:
            raise LocalTwoHumanCeremonyError("ceremony_state_invalid")
        if _parse_utc(row["expires_at"]) <= now:
            connection.execute(
                "UPDATE staging_two_human_ceremonies SET status='EXPIRED' "
                "WHERE ceremony_id=? AND control_tenant_id=? AND status IN ('REQUESTED','REQUESTER_APPROVED','REVIEWER_APPROVED')",
                (row["ceremony_id"], row["control_tenant_id"]),
            )
            connection.commit()
            raise LocalTwoHumanCeremonyError("ceremony_expired")

    @staticmethod
    def _payload(row, requester_subject: str, requester_key_id: str, reviewer_subject: str, reviewer_key_id: str) -> dict[str, str]:
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

    def create(self, human_session: Mapping[str, Any], confirmation: Mapping[str, Any]) -> dict[str, Any]:
        self._require_staging_runtime()
        ceremony_id = str(uuid4())
        human = self._authenticated_human(human_session, ceremony_id)
        release = _release_confirmation(confirmation)
        if release["control_tenant_id"] != human.tenant_id:
            raise LocalTwoHumanCeremonyError("tenant_scope_mismatch")
        release["control_tenant_id"] = human.tenant_id
        now = _now()
        expires = now + CEREMONY_TTL
        nonce = secrets.token_urlsafe(32)
        transaction_id = str(uuid4())
        with self.db.session() as connection:
            connection.execute(
                """INSERT INTO staging_two_human_ceremonies(
                   ceremony_id,status,authority_id,control_tenant_id,
                   approval_transaction_id,nonce,nonce_hash,environment,
                   database_target_identity,application_commit,repository_tree,
                   image_digest,issued_at,expires_at,requester_user_id,
                   requester_actor_id,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ceremony_id, "REQUESTED", release["authority_id"], release["control_tenant_id"],
                    transaction_id, nonce, hashlib.sha256(nonce.encode()).hexdigest(),
                    release["environment"], release["database_target_identity"],
                    release["application_commit"], release["repository_tree"],
                    release["image_digest"], _iso(now), _iso(expires), human.user_id,
                    human.actor_id, _iso(now),
                ),
            )
        self.audit.record(
            "STAGING_TWO_HUMAN_CEREMONY_CREATED", user_id=human.user_id,
            actor_id=human.actor_id, tenant_id=release["control_tenant_id"],
            resource_type="staging_two_human_ceremony", resource_id=ceremony_id,
            operation="create", outcome="requested",
            metadata={"ceremony_id": ceremony_id, "approval_transaction_id": transaction_id},
        )
        return {"ceremony_id": ceremony_id, "status": "REQUESTED", "issued_at": _iso(now), "expires_at": _iso(expires)}

    def approve(
        self,
        ceremony_id: str,
        role: str,
        human_session: Mapping[str, Any],
        confirmation: Mapping[str, Any],
        *,
        key_id: str,
        public_key: str,
        public_key_fingerprint: str,
        signature: str,
        counterparty_subject: str | None = None,
        counterparty_key_id: str | None = None,
    ) -> dict[str, Any]:
        self._require_staging_runtime()
        if role not in {"requester", "reviewer"}:
            raise LocalTwoHumanCeremonyError("role_invalid")
        human = self._authenticated_human(human_session, ceremony_id)
        release_confirmation = _release_confirmation(confirmation)
        key_id = str(key_id or "").strip()
        if not key_id or len(key_id) > 256:
            raise LocalTwoHumanCeremonyError("key_id_invalid")
        now = _now()
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM staging_two_human_ceremonies WHERE ceremony_id=? AND control_tenant_id=?",
                (str(ceremony_id), human.tenant_id),
            ).fetchone()
            if not row:
                raise LocalTwoHumanCeremonyError("ceremony_not_found")
            self._ensure_active(connection, row, now)
            if any(row[key] != release_confirmation[key] for key in set(EXPECTED_RELEASE) | {"authority_id", "control_tenant_id"}):
                raise LocalTwoHumanCeremonyError("release_confirmation_mismatch")
            if role == "requester":
                if row["status"] != "REQUESTED" or human.user_id != int(row["requester_user_id"]):
                    raise LocalTwoHumanCeremonyError("requester_role_denied")
            else:
                if row["status"] != "REQUESTER_APPROVED" or human.user_id == int(row["requester_user_id"]):
                    raise LocalTwoHumanCeremonyError("reviewer_role_denied")
            public_key_b64, fingerprint = _public_key_material(public_key, public_key_fingerprint)
            signature = _signature_shape(signature)
            prior = connection.execute(
                "SELECT a.* FROM staging_two_human_approvals a "
                "JOIN staging_two_human_ceremonies c ON c.ceremony_id=a.ceremony_id "
                "WHERE a.ceremony_id=? AND c.control_tenant_id=?",
                (str(ceremony_id), human.tenant_id),
            ).fetchall()
            for item in prior:
                if any(item[key] == value for key, value in (
                    ("human_user_id", human.user_id), ("actor_id", human.actor_id),
                    ("provider_subject", human.provider_subject),
                    ("credential_id", human.credential_id),
                    ("mfa_session_reference_hash", human.mfa_session_hash),
                    ("key_id", key_id), ("public_key_fingerprint", fingerprint),
                )):
                    raise LocalTwoHumanCeremonyError("requester_reviewer_identity_overlap")
            if role == "requester":
                other_subject = str(counterparty_subject or "").strip()
                other_key_id = str(counterparty_key_id or "").strip()
                if not other_subject or not other_key_id:
                    raise LocalTwoHumanCeremonyError("counterparty_binding_required")
                requester_subject, requester_key_id = human.provider_subject, key_id
                reviewer_subject, reviewer_key_id = other_subject, other_key_id
            else:
                requester_row = next((item for item in prior if item["role"] == "requester"), None)
                if requester_row is None:
                    raise LocalTwoHumanCeremonyError("requester_approval_required")
                requester_subject, requester_key_id = requester_row["provider_subject"], requester_row["key_id"]
                reviewer_subject, reviewer_key_id = human.provider_subject, key_id
                if counterparty_subject is not None and str(counterparty_subject).strip() != requester_subject:
                    raise LocalTwoHumanCeremonyError("counterparty_binding_mismatch")
                if counterparty_key_id is not None and str(counterparty_key_id).strip() != requester_key_id:
                    raise LocalTwoHumanCeremonyError("counterparty_binding_mismatch")
                other_subject, other_key_id = requester_subject, requester_key_id
            approval_payload = self._payload(row, requester_subject, requester_key_id, reviewer_subject, reviewer_key_id)
            try:
                signed_payload_hash = StagingAuthorityArtifactVerifier.verify_detached_signature(
                    approval_payload, signature, public_key_b64
                )
            except StagingAuthorityVerificationError as exc:
                raise LocalTwoHumanCeremonyError("signature_verification_failed") from exc
            approval_id = str(uuid4())
            connection.execute(
                """INSERT INTO staging_two_human_approvals(
                   approval_id,ceremony_id,role,human_user_id,actor_id,provider,
                   provider_subject,credential_id,mfa_session_reference_hash,
                   key_id,public_key,public_key_fingerprint,signature,
                   release_binding_hash,approved_at,result,counterparty_subject,
                   counterparty_key_id,signed_payload_hash)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    approval_id, ceremony_id, role, human.user_id, human.actor_id, PROVIDER,
                    human.provider_subject, human.credential_id, human.mfa_session_hash,
                    key_id, public_key_b64, fingerprint, signature,
                    _release_hash(release_confirmation), _iso(now), "APPROVED",
                    other_subject, other_key_id, signed_payload_hash,
                ),
            )
            next_state = "REQUESTER_APPROVED" if role == "requester" else "REVIEWER_APPROVED"
            connection.execute(
                "UPDATE staging_two_human_ceremonies SET status=? WHERE ceremony_id=? AND status=?",
                (next_state, ceremony_id, "REQUESTED" if role == "requester" else "REQUESTER_APPROVED"),
            )
        self.audit.record(
            "STAGING_TWO_HUMAN_" + role.upper() + "_APPROVED", user_id=human.user_id,
            actor_id=human.actor_id, tenant_id=release_confirmation["control_tenant_id"],
            resource_type="staging_two_human_ceremony", resource_id=ceremony_id,
            operation=role + "_approval", outcome="approved",
            metadata={
                "ceremony_id": ceremony_id, "role": role, "key_id": key_id,
                "public_key_fingerprint": fingerprint,
                "approval_id": approval_id,
                "mfa_session_reference_hash": human.mfa_session_hash,
                "release_binding_hash": _release_hash(release_confirmation),
                "approval_timestamp": _iso(now),
            },
        )
        return {"ceremony_id": ceremony_id, "status": next_state, "approval_id": approval_id, "approved_at": _iso(now)}

    def finalize(self, ceremony_id: str, human_session: Mapping[str, Any]) -> dict[str, Any]:
        self._require_staging_runtime()
        finalizer = self._authenticated_human(human_session, ceremony_id)
        now = _now()
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM staging_two_human_ceremonies WHERE ceremony_id=? AND control_tenant_id=?",
                (str(ceremony_id), finalizer.tenant_id),
            ).fetchone()
            if not row:
                raise LocalTwoHumanCeremonyError("ceremony_not_found")
            if finalizer.tenant_id != row["control_tenant_id"]:
                raise LocalTwoHumanCeremonyError("tenant_scope_mismatch")
            if row["status"] == "FINALIZED":
                raise LocalTwoHumanCeremonyError("duplicate_finalization")
            if row["status"] != "REVIEWER_APPROVED":
                raise LocalTwoHumanCeremonyError("both_approvals_required")
            self._ensure_active(connection, row, now)
            approvals = connection.execute(
                "SELECT a.* FROM staging_two_human_approvals a "
                "JOIN staging_two_human_ceremonies c ON c.ceremony_id=a.ceremony_id "
                "WHERE a.ceremony_id=? AND c.control_tenant_id=? ORDER BY a.role",
                (str(ceremony_id), finalizer.tenant_id),
            ).fetchall()
            if len(approvals) != 2 or {item["role"] for item in approvals} != {"requester", "reviewer"}:
                raise LocalTwoHumanCeremonyError("both_approvals_required")
            requester = next(item for item in approvals if item["role"] == "requester")
            reviewer = next(item for item in approvals if item["role"] == "reviewer")
            if finalizer.user_id != int(reviewer["human_user_id"]):
                raise LocalTwoHumanCeremonyError("finalizer_role_denied")
            payload = self._payload(row, requester["provider_subject"], requester["key_id"], reviewer["provider_subject"], reviewer["key_id"])
            if requester["signed_payload_hash"] != _digest(payload, PAYLOAD_FIELDS) or reviewer["signed_payload_hash"] != _digest(payload, PAYLOAD_FIELDS):
                raise LocalTwoHumanCeremonyError("approval_payload_binding_mismatch")
            manifest_unsigned = {
                "authority_id": row["authority_id"],
                "environment": row["environment"],
                "requester_subject": requester["provider_subject"],
                "requester_key_id": requester["key_id"],
                "requester_public_key_fingerprint": requester["public_key_fingerprint"],
                "reviewer_subject": reviewer["provider_subject"],
                "reviewer_key_id": reviewer["key_id"],
                "reviewer_public_key_fingerprint": reviewer["public_key_fingerprint"],
                "allowed_database_target_identity": row["database_target_identity"],
                "allowed_application_commit": row["application_commit"],
                "allowed_repository_tree": row["repository_tree"],
                "allowed_image_digest": row["image_digest"],
                "manifest_version": "1",
                "manifest_expiry": row["expires_at"],
                "authority_status": "active",
                "requester_key_status": "active",
                "reviewer_key_status": "active",
            }
            manifest = dict(
                manifest_unsigned,
                manifest_digest=hashlib.sha256(
                    _canonical(manifest_unsigned, MANIFEST_FIELDS - {"manifest_digest"})
                ).hexdigest(),
            )
            envelope = {
                "payload": payload,
                "requester_signature": requester["signature"],
                "reviewer_signature": reviewer["signature"],
            }
            resolver = {
                requester["key_id"]: requester["public_key"],
                reviewer["key_id"]: reviewer["public_key"],
            }
            try:
                verified = StagingAuthorityArtifactVerifier().verify(envelope, manifest, resolver)
            except Exception as exc:
                raise LocalTwoHumanCeremonyError("final_artifact_verification_failed") from exc
            artifact = {
                "ceremony_id": ceremony_id,
                "payload": payload,
                "manifest": manifest,
                "envelope": envelope,
                "artifact_hash": verified.artifact_hash,
                "approval_evidence": [
                    {
                        "role": item["role"], "human_user_id": int(item["human_user_id"]),
                        "actor_id": item["actor_id"], "provider": item["provider"],
                        "provider_subject": item["provider_subject"],
                        "credential_id": item["credential_id"],
                        "mfa_session_reference_hash": item["mfa_session_reference_hash"],
                        "key_id": item["key_id"],
                        "public_key_fingerprint": item["public_key_fingerprint"],
                        "approved_at": item["approved_at"], "result": item["result"],
                    }
                    for item in approvals
                ],
                "verification_metadata": {
                    "verifier": "StagingAuthorityArtifactVerifier",
                    "signature_domain": SIGNATURE_DOMAIN.decode("ascii"),
                    "key_resolver": resolver,
                },
            }
            artifact["artifact_integrity_hash"] = _artifact_integrity_hash(
                artifact["artifact_hash"], artifact["approval_evidence"], artifact["verification_metadata"], ceremony_id
            )
            updated = connection.execute(
                "UPDATE staging_two_human_ceremonies SET status='FINALIZED', artifact_hash=?, finalized_at=? "
                "WHERE ceremony_id=? AND control_tenant_id=? AND status='REVIEWER_APPROVED'",
                (verified.artifact_hash, _iso(now), ceremony_id, finalizer.tenant_id),
            )
            if updated.rowcount != 1:
                raise LocalTwoHumanCeremonyError("duplicate_finalization")
        self.audit.record(
            "STAGING_TWO_HUMAN_CEREMONY_FINALIZED",
            user_id=int(reviewer["human_user_id"]), actor_id=reviewer["actor_id"],
            tenant_id=row["control_tenant_id"], resource_type="staging_two_human_ceremony",
            resource_id=ceremony_id, operation="finalize", outcome="finalized",
            metadata={"ceremony_id": ceremony_id, "artifact_hash": verified.artifact_hash},
        )
        return artifact

    def cancel(self, ceremony_id: str, human_session: Mapping[str, Any]) -> dict[str, Any]:
        self._require_staging_runtime()
        human = self._authenticated_human(human_session, ceremony_id)
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM staging_two_human_ceremonies WHERE ceremony_id=? AND control_tenant_id=?", (ceremony_id, human.tenant_id)).fetchone()
            if not row:
                raise LocalTwoHumanCeremonyError("ceremony_not_found")
            self._ensure_active(connection, row, _now())
            if human.user_id != int(row["requester_user_id"]):
                raise LocalTwoHumanCeremonyError("cancel_role_denied")
            connection.execute("UPDATE staging_two_human_ceremonies SET status='CANCELLED' WHERE ceremony_id=?", (ceremony_id,))
        self.audit.record("STAGING_TWO_HUMAN_CEREMONY_CANCELLED", user_id=human.user_id, actor_id=human.actor_id, tenant_id=row["control_tenant_id"], resource_type="staging_two_human_ceremony", resource_id=ceremony_id, operation="cancel", outcome="cancelled")
        return {"ceremony_id": ceremony_id, "status": "CANCELLED"}


def _release_hash(release: Mapping[str, str]) -> str:
    return hashlib.sha256(json.dumps(dict(sorted(release.items())), separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _artifact_integrity_hash(artifact_hash: str, evidence: list[Mapping[str, Any]], metadata: Mapping[str, Any], ceremony_id: str) -> str:
    binding = {
        "artifact_hash": artifact_hash,
        "approval_evidence_json": json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        "verification_metadata_json": json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        "ceremony_id": ceremony_id,
    }
    return _digest(binding, frozenset(binding))


def verify_final_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Offline verification adapter for a finalized artifact."""
    required = {"ceremony_id", "payload", "manifest", "envelope", "artifact_hash", "approval_evidence", "verification_metadata", "artifact_integrity_hash"}
    if set(artifact) != required:
        raise StagingAuthorityVerificationError("final_artifact_fields_invalid")
    envelope = artifact["envelope"]
    manifest = artifact["manifest"]
    payload = artifact["payload"]
    if artifact["artifact_hash"] != _digest(payload, PAYLOAD_FIELDS):
        raise StagingAuthorityVerificationError("final_artifact_hash_mismatch")
    if artifact["artifact_integrity_hash"] != _artifact_integrity_hash(
        artifact["artifact_hash"], artifact["approval_evidence"], artifact["verification_metadata"], artifact["ceremony_id"]
    ):
        raise StagingAuthorityVerificationError("final_artifact_integrity_hash_mismatch")
    evidence = artifact["approval_evidence"]
    if not isinstance(evidence, list) or len(evidence) != 2 or {item.get("role") for item in evidence} != {"requester", "reviewer"}:
        raise StagingAuthorityVerificationError("final_artifact_approval_evidence_invalid")
    requester_evidence = next(item for item in evidence if item.get("role") == "requester")
    reviewer_evidence = next(item for item in evidence if item.get("role") == "reviewer")
    for field in (
        "human_user_id", "actor_id", "provider_subject", "credential_id",
        "mfa_session_reference_hash", "key_id", "public_key_fingerprint",
    ):
        if requester_evidence.get(field) == reviewer_evidence.get(field):
            raise StagingAuthorityVerificationError("final_artifact_identity_overlap")
    if requester_evidence.get("key_id") != payload["requester_key_id"] or reviewer_evidence.get("key_id") != payload["reviewer_key_id"]:
        raise StagingAuthorityVerificationError("final_artifact_key_binding_mismatch")
    if requester_evidence.get("provider_subject") != payload["requester_subject"] or reviewer_evidence.get("provider_subject") != payload["reviewer_subject"]:
        raise StagingAuthorityVerificationError("final_artifact_subject_binding_mismatch")
    resolver = artifact.get("verification_metadata", {}).get("key_resolver")
    if not isinstance(resolver, Mapping):
        raise StagingAuthorityVerificationError("final_artifact_key_resolver_missing")
    ceremony = StagingAuthorityArtifactVerifier().verify(envelope, manifest, resolver)
    return {"verified": True, "artifact_hash": ceremony.artifact_hash, "payload": dict(ceremony.payload)}


__all__ = ["EXPECTED_RELEASE", "LocalTwoHumanCeremonyError", "LocalTwoHumanStagingCeremony", "verify_final_artifact"]


local_two_human_ceremony_api = Blueprint(
    "local_two_human_ceremony_api", __name__, url_prefix="/api/staging/authority-ceremony"
)


def _csrf_ok() -> bool:
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    return bool(expected and supplied and hmac.compare_digest(str(expected), str(supplied)))


def _coordinator() -> LocalTwoHumanStagingCeremony:
    container = current_app.container
    return LocalTwoHumanStagingCeremony(
        database,
        auth=container.require("auth_service"),
        mfa=container.require("mfa_service"),
        audit=container.require("audit_service"),
        authority=container.require("canonical_authority"),
    )


def _json() -> dict[str, Any]:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise LocalTwoHumanCeremonyError("json_object_required")
    return value


def _failure(exc: Exception):
    code = str(exc)
    status = 403 if code in {"csrf_validation_failed", "mfa_session_invalid", "authenticated_mfa_account_required"} else 400
    if code == "ceremony_not_found":
        status = 404
    return jsonify({"error": code}), status


@local_two_human_ceremony_api.post("")
def create_ceremony():
    if not _csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    try:
        data = _json()
        return jsonify(_coordinator().create(session, data.get("release_confirmation"))), 201
    except LocalTwoHumanCeremonyError as exc:
        return _failure(exc)


def _approve(ceremony_id: str, role: str):
    if not _csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    try:
        data = _json()
        return jsonify(_coordinator().approve(
            ceremony_id, role, session, data.get("release_confirmation"),
            key_id=data.get("key_id"), public_key=data.get("public_key"),
            public_key_fingerprint=data.get("public_key_fingerprint"),
            signature=data.get("signature"),
            counterparty_subject=data.get("counterparty_subject"),
            counterparty_key_id=data.get("counterparty_key_id"),
        )), 200
    except LocalTwoHumanCeremonyError as exc:
        return _failure(exc)


@local_two_human_ceremony_api.post("/<ceremony_id>/requester-approval")
def requester_approval(ceremony_id: str):
    return _approve(ceremony_id, "requester")


@local_two_human_ceremony_api.post("/<ceremony_id>/reviewer-approval")
def reviewer_approval(ceremony_id: str):
    return _approve(ceremony_id, "reviewer")


@local_two_human_ceremony_api.post("/<ceremony_id>/finalize")
def finalize_ceremony(ceremony_id: str):
    if not _csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    try:
        artifact = _coordinator().finalize(ceremony_id, session)
        return jsonify(artifact), 200
    except LocalTwoHumanCeremonyError as exc:
        return _failure(exc)


@local_two_human_ceremony_api.post("/<ceremony_id>/cancel")
def cancel_ceremony(ceremony_id: str):
    if not _csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    try:
        return jsonify(_coordinator().cancel(ceremony_id, session)), 200
    except LocalTwoHumanCeremonyError as exc:
        return _failure(exc)


__all__.append("local_two_human_ceremony_api")
