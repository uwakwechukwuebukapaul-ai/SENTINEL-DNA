"""Fail-closed requester/reviewer approval workflow.

This module consumes the existing verified Entra token result and binding
repository. It does not validate tokens, create users, or activate any
deployment/custody workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Callable, Mapping
from uuid import uuid4

from database.connection import DatabaseConnection, database
from .entra_oidc import EntraBindingRepository, EntraIdentityTuple, EntraOidcError, VerifiedEntraToken


REQUEST_APPROVAL = "REQUEST_APPROVAL"
VIEW_OWN_REQUEST = "VIEW_OWN_REQUEST"
REVIEW_APPROVAL = "REVIEW_APPROVAL"
REJECT_APPROVAL = "REJECT_APPROVAL"
VIEW_APPROVAL_AUDIT = "VIEW_APPROVAL_AUDIT"

_IDENTITY_FIELDS = ("issuer", "tenant_id", "object_id", "subject_id")
_SENSITIVE_KEY_PARTS = ("password", "secret", "token", "credential", "private_key", "access_key")
_HEX_HASH = re.compile(r"^[0-9a-f]{64}$")
_CONTEXT_TOKEN = object()


class ApprovalWorkflowError(ValueError):
    pass


@dataclass(frozen=True)
class AuthenticatedEntraContext:
    """The verified identity/session boundary handed to workflow methods."""

    identity: EntraIdentityTuple
    user_id: int
    roles: frozenset[str]
    session_version: int
    tenant_id: str
    actor_id: str
    _context_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._context_token is not _CONTEXT_TOKEN:
            raise ApprovalWorkflowError("authenticated_entra_context_untrusted")


def resolve_authenticated_entra_context(
    verified: VerifiedEntraToken,
    *,
    db: DatabaseConnection = database,
    auth_service: Any,
    session_version: int,
) -> AuthenticatedEntraContext:
    """Resolve a validator-produced Entra result to an active local session."""
    if not isinstance(verified, VerifiedEntraToken):
        raise ApprovalWorkflowError("verified_entra_context_required")
    verified.identity.validate()
    binding = EntraBindingRepository(db).resolve(verified.identity)
    user_id = int(binding["user_id"])
    user = auth_service.session_user(user_id, session_version)
    if user is None or not user.is_active or not user.tenant_id or not user.actor_id:
        raise ApprovalWorkflowError("local_session_invalid")
    with db.session() as connection:
        membership = connection.execute(
            """SELECT m.status, i.status AS identity_status, t.status AS tenant_status
               FROM canonical_memberships m
               JOIN canonical_identities i ON i.actor_id=m.actor_id
               JOIN canonical_tenants t ON t.tenant_id=m.tenant_id
               WHERE m.tenant_id=? AND m.actor_id=?""",
            (user.tenant_id, user.actor_id),
        ).fetchone()
    if not membership or membership["status"] != "active" or membership["identity_status"] != "active" or membership["tenant_status"] != "active":
        raise ApprovalWorkflowError("membership_inactive")
    return AuthenticatedEntraContext(
        identity=verified.identity,
        user_id=user_id,
        roles=frozenset(verified.roles),
        session_version=int(session_version),
        tenant_id=str(user.tenant_id),
        actor_id=str(user.actor_id),
        _context_token=_CONTEXT_TOKEN,
    )


def request_hash(artifact: Mapping[str, Any]) -> str:
    if not isinstance(artifact, Mapping):
        raise ApprovalWorkflowError("approval_artifact_invalid")
    def reject_sensitive(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if any(part in str(key).lower().replace("-", "_") for part in _SENSITIVE_KEY_PARTS):
                    raise ApprovalWorkflowError("approval_artifact_contains_sensitive_field")
                reject_sensitive(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                reject_sensitive(item)
    reject_sensitive(artifact)
    try:
        encoded = json.dumps(artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ApprovalWorkflowError("approval_artifact_invalid") from exc
    return hashlib.sha256(encoded).hexdigest()


def _identity_values(identity: EntraIdentityTuple) -> tuple[str, str, str, str]:
    identity.validate()
    return identity.issuer, identity.tenant_id, identity.object_id, identity.subject_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprovalWorkflow:
    CAPABILITIES = {
        REQUEST_APPROVAL: "sdna.requester",
        VIEW_OWN_REQUEST: "sdna.requester",
        REVIEW_APPROVAL: "sdna.reviewer",
        REJECT_APPROVAL: "sdna.reviewer",
        VIEW_APPROVAL_AUDIT: "sdna.reviewer",
    }

    def __init__(self, db: DatabaseConnection = database, *, reauthenticate: Callable[[AuthenticatedEntraContext], bool] | None = None):
        self.db = db
        self.reauthenticate = reauthenticate

    def _require(self, context: AuthenticatedEntraContext, capability: str) -> None:
        if not isinstance(context, AuthenticatedEntraContext):
            raise ApprovalWorkflowError("authenticated_entra_context_required")
        context.identity.validate()
        required_role = self.CAPABILITIES[capability]
        if required_role not in context.roles:
            raise ApprovalWorkflowError("capability_denied")

    def _require_reauthentication(self, context: AuthenticatedEntraContext) -> None:
        if self.reauthenticate is None or not bool(self.reauthenticate(context)):
            raise ApprovalWorkflowError("fresh_reauthentication_required")

    def create_request(
        self,
        context: AuthenticatedEntraContext,
        artifact: Mapping[str, Any],
        *,
        expires_at: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        self._require(context, REQUEST_APPROVAL)
        self._require_reauthentication(context)
        digest = request_hash(artifact)
        created_at = _now()
        expiry = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        if not approval_id:
            approval_id = str(uuid4())
        if not _HEX_HASH.fullmatch(digest):
            raise ApprovalWorkflowError("request_hash_invalid")
        values = _identity_values(context.identity)
        with self.db.session() as connection:
            connection.execute(
                """INSERT INTO approval_requests(
                    approval_id,request_hash,requester_issuer,requester_tenant_id,
                    requester_object_id,requester_subject_id,requester_user_id,
                    requester_role,created_at,expires_at,status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (approval_id, digest, *values, context.user_id, "sdna.requester", created_at, expiry, "pending"),
            )
            self._audit(connection, approval_id, digest, context, "REQUEST_APPROVAL", created_at, str(uuid4()), "none", "pending")
        return {"approval_id": approval_id, "request_hash": digest, "status": "pending", "created_at": created_at, "expires_at": expiry}

    def get_own_request(self, context: AuthenticatedEntraContext, approval_id: str) -> dict[str, Any]:
        self._require(context, VIEW_OWN_REQUEST)
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM approval_requests WHERE approval_id=? AND requester_user_id=? AND requester_issuer=? AND requester_tenant_id=? AND requester_object_id=? AND requester_subject_id=?",
                (approval_id, context.user_id, *_identity_values(context.identity)),
            ).fetchone()
        if not row:
            raise ApprovalWorkflowError("approval_not_found")
        return dict(row)

    def approve(self, context: AuthenticatedEntraContext, approval_id: str, artifact: Mapping[str, Any], *, approval_transaction_id: str | None = None) -> dict[str, Any]:
        return self._decide(context, approval_id, artifact, "approved", REVIEW_APPROVAL, approval_transaction_id)

    def reject(self, context: AuthenticatedEntraContext, approval_id: str, artifact: Mapping[str, Any], *, approval_transaction_id: str | None = None) -> dict[str, Any]:
        return self._decide(context, approval_id, artifact, "rejected", REJECT_APPROVAL, approval_transaction_id)

    def _decide(self, context: AuthenticatedEntraContext, approval_id: str, artifact: Mapping[str, Any], decision: str, capability: str, approval_transaction_id: str | None) -> dict[str, Any]:
        self._require(context, capability)
        self._require_reauthentication(context)
        if not approval_transaction_id:
            approval_transaction_id = str(uuid4())
        digest = request_hash(artifact)
        now = _now()
        values = _identity_values(context.identity)
        with self.db.session() as connection:
            if connection.execute(
                "SELECT 1 FROM approval_decisions WHERE approval_transaction_id=?",
                (approval_transaction_id,),
            ).fetchone():
                raise ApprovalWorkflowError("approval_transaction_id_already_used")
            row = connection.execute(
                "SELECT request_hash,status,expires_at,requester_issuer,requester_tenant_id,requester_object_id,requester_subject_id,requester_user_id FROM approval_requests WHERE approval_id=?",
                (approval_id,),
            ).fetchone()
            if not row:
                raise ApprovalWorkflowError("approval_not_found")
            if row["request_hash"] != digest:
                raise ApprovalWorkflowError("request_hash_mismatch")
            if tuple(row[key] for key in ("requester_issuer", "requester_tenant_id", "requester_object_id", "requester_subject_id")) == values:
                raise ApprovalWorkflowError("requester_reviewer_same_identity")
            if row["status"] != "pending":
                raise ApprovalWorkflowError("approval_already_consumed")
            if str(row["expires_at"]) <= now:
                connection.execute("UPDATE approval_requests SET status='expired' WHERE approval_id=? AND status='pending'", (approval_id,))
                self._audit(connection, approval_id, digest, context, "EXPIRE_APPROVAL", now, approval_transaction_id, "pending", "expired")
                raise ApprovalWorkflowError("approval_expired")
            updated = connection.execute(
                "UPDATE approval_requests SET status=?, consumed_at=? WHERE approval_id=? AND request_hash=? AND status='pending'",
                (decision, now, approval_id, digest),
            )
            if updated.rowcount != 1:
                raise ApprovalWorkflowError("approval_already_consumed")
            connection.execute(
                """INSERT INTO approval_decisions(
                    approval_id,request_hash,reviewer_issuer,reviewer_tenant_id,
                    reviewer_object_id,reviewer_subject_id,reviewer_user_id,
                    reviewer_role,approved_at,decision,approval_transaction_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (approval_id, digest, *values, context.user_id, "sdna.reviewer", now, decision, approval_transaction_id),
            )
            self._audit(connection, approval_id, digest, context, "APPROVE_APPROVAL" if decision == "approved" else "REJECT_APPROVAL", now, approval_transaction_id, "pending", decision)
        return {"approval_id": approval_id, "request_hash": digest, "status": decision, "approval_transaction_id": approval_transaction_id}

    def list_audit(self, context: AuthenticatedEntraContext, approval_id: str) -> list[dict[str, Any]]:
        self._require(context, VIEW_APPROVAL_AUDIT)
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM approval_audit_events WHERE approval_id=? ORDER BY occurred_at,event_id",
                (approval_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _audit(connection: Any, approval_id: str, digest: str, context: AuthenticatedEntraContext, action: str, occurred_at: str, transaction_id: str, previous_status: str, new_status: str) -> None:
        issuer, tenant_id, object_id, subject_id = _identity_values(context.identity)
        role = "sdna.requester" if action == "REQUEST_APPROVAL" else "sdna.reviewer"
        connection.execute(
            """INSERT INTO approval_audit_events(
                event_id,approval_id,request_hash,subject_id,issuer,tenant_id,
                object_id,user_id,role,action,occurred_at,transaction_id,
                previous_status,new_status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid4()), approval_id, digest, subject_id, issuer, tenant_id, object_id, context.user_id, role, action, occurred_at, transaction_id, previous_status, new_status),
        )


__all__ = [
    "ApprovalWorkflow", "ApprovalWorkflowError", "AuthenticatedEntraContext",
    "REQUEST_APPROVAL", "VIEW_OWN_REQUEST", "REVIEW_APPROVAL", "REJECT_APPROVAL",
    "VIEW_APPROVAL_AUDIT", "request_hash", "resolve_authenticated_entra_context",
]
