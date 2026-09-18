"""Dedicated, staging-only authorization contract for first privileged bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any, Mapping
from uuid import uuid4

from database.canonical_authority import CanonicalUnitOfWork
from database.connection import DatabaseConnection, database
from services.audit.service import AuditService
from services.auth.permissions import PERMISSIONS
from services.identity.authentication import (
    AuthenticatedProviderPrincipal,
    CanonicalAuthenticationBoundary,
    CanonicalAuthenticationPrincipal,
)
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContext


BOOTSTRAP_OPERATION = "staging_first_privileged_identity_bootstrap"
BOOTSTRAP_PURPOSE = "create_first_staging_control_tenant_soc_manager"
BOOTSTRAP_ENVIRONMENT = "staging"
BOOTSTRAP_ROLE = "soc_manager"
REQUEST_CAPABILITY = "identity:staging_bootstrap_request"
APPROVE_CAPABILITY = "identity:staging_bootstrap_approve"
STATES = frozenset({"REQUESTED", "APPROVED", "REJECTED", "EXPIRED", "CONSUMED"})
APPROVED_REVIEWER_ROLES = frozenset({"admin", "soc_manager"})
SENSITIVE_KEYS = frozenset({
    "password", "password_hash", "token", "secret", "credential", "cookie",
    "csrf", "private_key", "recovery_code", "tailscale",
})


class StagingBootstrapAuthorizationError(RuntimeError):
    """Safe, non-secret error for bootstrap authorization failures."""


@dataclass(frozen=True)
class VerifiedBootstrapPrincipal:
    """Provider-verified principal resolved to a live canonical application user."""

    provider: str
    subject: str
    credential_id: str
    actor_id: str
    user_id: int
    tenant_id: str
    context: CanonicalRequestContext
    verified_at: str

    @classmethod
    def from_provider_principal(
        cls,
        principal: AuthenticatedProviderPrincipal,
        *,
        boundary: CanonicalAuthenticationBoundary,
        db: DatabaseConnection = database,
    ) -> "VerifiedBootstrapPrincipal":
        if not isinstance(principal, AuthenticatedProviderPrincipal):
            raise StagingBootstrapAuthorizationError("verified_principal_required")
        fields = (
            principal.provider, principal.subject, principal.tenant_id,
            principal.actor_id, principal.authentication_method,
            principal.credential_id,
        )
        if not all(str(value or "").strip() for value in fields):
            raise StagingBootstrapAuthorizationError("verified_principal_incomplete")
        try:
            context = boundary.compose(
                CanonicalAuthenticationPrincipal(
                    tenant_id=principal.tenant_id,
                    actor_id=principal.actor_id,
                    authentication_method=principal.authentication_method,
                    credential_id=principal.credential_id,
                )
            )
        except Exception as exc:
            raise StagingBootstrapAuthorizationError("verified_principal_denied") from exc
        if context.tenant_id != principal.tenant_id or context.actor_id != principal.actor_id:
            raise StagingBootstrapAuthorizationError("verified_principal_mismatch")
        external_subject = principal.external_subject.strip() or principal.subject.strip()
        with db.session() as connection:
            binding = connection.execute(
                """SELECT actor_id FROM canonical_identity_bindings
                   WHERE provider=? AND external_subject=? AND actor_id=? AND status='active'""",
                (principal.provider.strip(), external_subject, principal.actor_id.strip()),
            ).fetchone()
            user = connection.execute(
                """SELECT id FROM users
                   WHERE actor_id=? AND tenant_id=? AND is_active=1
                     AND COALESCE(revocation_status, 'active')='active'""",
                (principal.actor_id.strip(), principal.tenant_id.strip()),
            ).fetchone()
        if not binding or not user:
            raise StagingBootstrapAuthorizationError("verified_identity_provenance_required")
        return cls(
            provider=principal.provider.strip(),
            subject=external_subject,
            credential_id=principal.credential_id.strip(),
            actor_id=principal.actor_id.strip(),
            user_id=int(user["id"]),
            tenant_id=principal.tenant_id.strip(),
            context=context,
            verified_at=datetime.now(timezone.utc).isoformat(),
        )


def _utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: str | datetime) -> str:
    return _utc(value).isoformat()


def _normalized_target(username: str, email: str) -> tuple[str, str]:
    normalized_username = str(username or "").strip()
    normalized_email = str(email or "").strip().lower()
    if not normalized_username or not normalized_email:
        raise StagingBootstrapAuthorizationError("target_identity_required")
    return normalized_username, normalized_email


def canonical_artifact(
    *,
    operation: str,
    purpose: str,
    environment: str,
    control_tenant_id: str,
    target_username: str,
    target_email: str,
    target_role: str,
    database_target_identity: str,
    requester_actor_id: str,
    approval_transaction_id: str,
    expires_at: str | datetime,
) -> dict[str, str]:
    username, email = _normalized_target(target_username, target_email)
    artifact = {
        "operation": str(operation).strip(),
        "purpose": str(purpose).strip(),
        "environment": str(environment).strip().lower(),
        "control_tenant_id": str(control_tenant_id).strip(),
        "target_username": username,
        "target_email": email,
        "target_role": str(target_role).strip().lower(),
        "database_target_identity": str(database_target_identity).strip(),
        "requester_actor_id": str(requester_actor_id).strip(),
        "approval_transaction_id": str(approval_transaction_id).strip(),
        "expires_at": _iso_utc(expires_at),
    }
    if not all(artifact.values()):
        raise StagingBootstrapAuthorizationError("approval_artifact_invalid")
    return artifact


def _canonical_bytes(artifact: Mapping[str, str]) -> bytes:
    expected = {
        "operation", "purpose", "environment", "control_tenant_id",
        "target_username", "target_email", "target_role",
        "database_target_identity", "requester_actor_id",
        "approval_transaction_id", "expires_at",
    }
    if set(artifact) != expected:
        raise StagingBootstrapAuthorizationError("approval_artifact_invalid")
    if any(str(key).lower() in SENSITIVE_KEYS for key in artifact):
        raise StagingBootstrapAuthorizationError("approval_artifact_contains_sensitive_field")
    return json.dumps(dict(sorted(artifact.items())), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def artifact_hash(artifact: Mapping[str, str]) -> str:
    return hashlib.sha256(_canonical_bytes(artifact)).hexdigest()


def _require_active_context(principal: VerifiedBootstrapPrincipal, tenant_id: str) -> None:
    if principal.context.tenant_id != tenant_id or principal.tenant_id != tenant_id:
        raise StagingBootstrapAuthorizationError("tenant_scope_mismatch")
    if principal.context.actor_id != principal.actor_id:
        raise StagingBootstrapAuthorizationError("principal_context_mismatch")
    if principal.context.tenant.status != "active":
        raise StagingBootstrapAuthorizationError("control_tenant_inactive")
    if principal.context.identity.status != "active" or principal.context.membership.status != "active":
        raise StagingBootstrapAuthorizationError("principal_inactive")


def _require_request_capability(principal: VerifiedBootstrapPrincipal) -> None:
    if principal.context.role.lower() not in PERMISSIONS.get(REQUEST_CAPABILITY, set()):
        raise StagingBootstrapAuthorizationError("capability_denied")


def _require_approval_capability(principal: VerifiedBootstrapPrincipal) -> None:
    if principal.context.role.lower() not in PERMISSIONS.get(APPROVE_CAPABILITY, set()):
        raise StagingBootstrapAuthorizationError("capability_denied")


@dataclass(frozen=True)
class BootstrapAuthorization:
    authorization_id: str
    approval_transaction_id: str
    artifact_hash: str
    status: str
    control_tenant_id: str
    requester_actor_id: str
    requester_user_id: int
    reviewer_actor_id: str | None
    reviewer_user_id: int | None
    target_username: str
    target_email: str
    target_role: str
    environment: str
    database_target_identity: str
    expires_at: str


class StagingBootstrapAuthorizationService:
    """Create, approve, and consume the dedicated staging bootstrap contract."""

    def __init__(
        self,
        db: DatabaseConnection = database,
        *,
        authority: CanonicalAuthorityService | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self.db = db
        self.authority = authority or CanonicalAuthorityService(db)
        self.audit = audit or AuditService(db)

    @staticmethod
    def _row(row: Any) -> BootstrapAuthorization:
        if not row:
            raise StagingBootstrapAuthorizationError("approval_not_found")
        return BootstrapAuthorization(
            authorization_id=row["authorization_id"],
            approval_transaction_id=row["approval_transaction_id"],
            artifact_hash=row["artifact_hash"],
            status=row["status"],
            control_tenant_id=row["control_tenant_id"],
            requester_actor_id=row["requester_actor_id"],
            requester_user_id=int(row["requester_user_id"]),
            reviewer_actor_id=row["reviewer_actor_id"],
            reviewer_user_id=int(row["reviewer_user_id"]) if row["reviewer_user_id"] is not None else None,
            target_username=row["target_username"],
            target_email=row["target_email"],
            target_role=row["target_role"],
            environment=row["environment"],
            database_target_identity=row["database_target_identity"],
            expires_at=row["expires_at"],
        )

    def create_request(
        self,
        requester: VerifiedBootstrapPrincipal,
        *,
        control_tenant_id: str,
        target_username: str,
        target_email: str,
        database_target_identity: str,
        expires_at: str | datetime,
        approval_transaction_id: str | None = None,
    ) -> BootstrapAuthorization:
        _require_active_context(requester, control_tenant_id)
        _require_request_capability(requester)
        transaction_id = str(approval_transaction_id or uuid4()).strip()
        expiry = _iso_utc(expires_at)
        if _utc(expiry) <= datetime.now(timezone.utc):
            raise StagingBootstrapAuthorizationError("approval_expired")
        artifact = canonical_artifact(
            operation=BOOTSTRAP_OPERATION,
            purpose=BOOTSTRAP_PURPOSE,
            environment=BOOTSTRAP_ENVIRONMENT,
            control_tenant_id=control_tenant_id,
            target_username=target_username,
            target_email=target_email,
            target_role=BOOTSTRAP_ROLE,
            database_target_identity=database_target_identity,
            requester_actor_id=requester.actor_id,
            approval_transaction_id=transaction_id,
            expires_at=expiry,
        )
        authorization_id = str(uuid4())
        with CanonicalUnitOfWork(self.db) as unit:
            tenant = self.authority.tenants.get(control_tenant_id, connection=unit.conn)
            if not tenant or tenant.status != "active":
                raise StagingBootstrapAuthorizationError("control_tenant_inactive")
            unit.conn.execute(
                """INSERT INTO staging_bootstrap_authorizations(
                   authorization_id,control_tenant_id,requester_actor_id,requester_user_id,
                   requester_provider,requester_subject,requester_credential_id,requester_verified_at,
                   operation,purpose,environment,target_username,target_email,target_role,
                   database_target_identity,approval_transaction_id,artifact_hash,expires_at,status,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    authorization_id, control_tenant_id, requester.actor_id, requester.user_id,
                    requester.provider, requester.subject, requester.credential_id, requester.verified_at,
                    BOOTSTRAP_OPERATION, BOOTSTRAP_PURPOSE, BOOTSTRAP_ENVIRONMENT,
                    artifact["target_username"], artifact["target_email"], BOOTSTRAP_ROLE,
                    database_target_identity, transaction_id, artifact_hash(artifact), expiry,
                    "REQUESTED", datetime.now(timezone.utc).isoformat(),
                ),
            )
            self.audit.record(
                "STAGING_BOOTSTRAP_REQUESTED",
                tenant_id=control_tenant_id,
                actor_id=requester.actor_id,
                user_id=requester.user_id,
                operation=BOOTSTRAP_OPERATION,
                outcome="requested",
                metadata={"authorization_id": authorization_id, "approval_transaction_id": transaction_id},
                connection=unit.conn,
            )
        return self.get(authorization_id)

    def get(self, authorization_id: str, *, connection: Any | None = None) -> BootstrapAuthorization:
        if connection is not None:
            return self._row(connection.execute(
                "SELECT * FROM staging_bootstrap_authorizations WHERE authorization_id=?",
                (str(authorization_id),),
            ).fetchone())
        with self.db.session() as owned:
            return self._row(owned.execute(
                "SELECT * FROM staging_bootstrap_authorizations WHERE authorization_id=?",
                (str(authorization_id),),
            ).fetchone())

    def approve(
        self,
        reviewer: VerifiedBootstrapPrincipal,
        authorization_id: str,
        *,
        artifact: Mapping[str, str] | None = None,
    ) -> BootstrapAuthorization:
        current = self.get(authorization_id)
        _require_active_context(reviewer, current.control_tenant_id)
        if reviewer.actor_id == current.requester_actor_id:
            raise StagingBootstrapAuthorizationError("requester_reviewer_same_identity")
        _require_approval_capability(reviewer)
        now = datetime.now(timezone.utc)
        if current.status != "REQUESTED":
            raise StagingBootstrapAuthorizationError("approval_state_invalid")
        if _utc(current.expires_at) <= now:
            self._expire(authorization_id)
            raise StagingBootstrapAuthorizationError("approval_expired")
        if artifact is not None and not hmac.compare_digest(artifact_hash(artifact), current.artifact_hash):
            raise StagingBootstrapAuthorizationError("request_hash_mismatch")
        with CanonicalUnitOfWork(self.db) as unit:
            cursor = unit.conn.execute(
                """UPDATE staging_bootstrap_authorizations
                   SET status='APPROVED', reviewer_actor_id=?, reviewer_user_id=?,
                       reviewer_provider=?, reviewer_subject=?, reviewer_credential_id=?,
                       reviewer_verified_at=?, decided_at=?
                   WHERE authorization_id=? AND status='REQUESTED'""",
                (
                    reviewer.actor_id, reviewer.user_id, reviewer.provider, reviewer.subject,
                    reviewer.credential_id, reviewer.verified_at, now.isoformat(), authorization_id,
                ),
            )
            if cursor.rowcount != 1:
                raise StagingBootstrapAuthorizationError("approval_state_invalid")
            self.audit.record(
                "STAGING_BOOTSTRAP_APPROVED",
                tenant_id=current.control_tenant_id,
                actor_id=reviewer.actor_id,
                user_id=reviewer.user_id,
                operation=BOOTSTRAP_OPERATION,
                outcome="approved",
                metadata={
                    "authorization_id": authorization_id,
                    "requester_actor_id": current.requester_actor_id,
                    "requester_user_id": current.requester_user_id,
                    "reviewer_actor_id": reviewer.actor_id,
                    "reviewer_user_id": reviewer.user_id,
                },
                connection=unit.conn,
            )
        return self.get(authorization_id)

    def reject(self, reviewer: VerifiedBootstrapPrincipal, authorization_id: str) -> BootstrapAuthorization:
        current = self.get(authorization_id)
        _require_active_context(reviewer, current.control_tenant_id)
        if reviewer.actor_id == current.requester_actor_id:
            raise StagingBootstrapAuthorizationError("requester_reviewer_same_identity")
        _require_approval_capability(reviewer)
        if current.status != "REQUESTED":
            raise StagingBootstrapAuthorizationError("approval_state_invalid")
        with CanonicalUnitOfWork(self.db) as unit:
            cursor = unit.conn.execute(
                "UPDATE staging_bootstrap_authorizations SET status='REJECTED', reviewer_actor_id=?, reviewer_user_id=?, reviewer_provider=?, reviewer_subject=?, reviewer_credential_id=?, reviewer_verified_at=?, decided_at=? WHERE authorization_id=? AND status='REQUESTED'",
                (reviewer.actor_id, reviewer.user_id, reviewer.provider, reviewer.subject, reviewer.credential_id, reviewer.verified_at, datetime.now(timezone.utc).isoformat(), authorization_id),
            )
            if cursor.rowcount != 1:
                raise StagingBootstrapAuthorizationError("approval_state_invalid")
        return self.get(authorization_id)

    def _expire(self, authorization_id: str, *, connection: Any | None = None) -> None:
        if connection is not None:
            connection.execute("UPDATE staging_bootstrap_authorizations SET status='EXPIRED' WHERE authorization_id=? AND status IN ('REQUESTED','APPROVED')", (authorization_id,))
            return
        with self.db.session() as owned:
            self._expire(authorization_id, connection=owned)

    def consume(
        self,
        connection: Any,
        *,
        authorization_id: str,
        approval_transaction_id: str,
        artifact: Mapping[str, str],
        control_tenant_id: str,
        correlation_id: str,
        created_user_id: int,
        created_actor_id: str,
        now: datetime | None = None,
    ) -> BootstrapAuthorization:
        from services.auth.privileged_provisioning import acquire_privileged_tenant_transaction_lock

        acquire_privileged_tenant_transaction_lock(connection, control_tenant_id)
        current = self.get(authorization_id, connection=connection)
        now = now or datetime.now(timezone.utc)
        if current.status != "APPROVED":
            raise StagingBootstrapAuthorizationError("approval_not_approved")
        if current.control_tenant_id != control_tenant_id:
            raise StagingBootstrapAuthorizationError("approval_scope_mismatch")
        if current.approval_transaction_id != str(approval_transaction_id):
            raise StagingBootstrapAuthorizationError("approval_transaction_mismatch")
        if _utc(current.expires_at) <= now:
            self._expire(authorization_id, connection=connection)
            raise StagingBootstrapAuthorizationError("approval_expired")
        if not hmac.compare_digest(artifact_hash(artifact), current.artifact_hash):
            raise StagingBootstrapAuthorizationError("request_hash_mismatch")
        if artifact.get("control_tenant_id") != control_tenant_id or artifact.get("target_role") != BOOTSTRAP_ROLE:
            raise StagingBootstrapAuthorizationError("approval_scope_mismatch")
        cursor = connection.execute(
            "UPDATE staging_bootstrap_authorizations SET status='CONSUMED', consumed_at=?, bootstrap_correlation_id=?, created_user_id=?, created_actor_id=? WHERE authorization_id=? AND status='APPROVED'",
            (now.isoformat(), correlation_id, int(created_user_id), str(created_actor_id), authorization_id),
        )
        if cursor.rowcount != 1:
            raise StagingBootstrapAuthorizationError("approval_already_consumed")
        connection.execute(
            """INSERT INTO staging_bootstrap_consumptions(
               bootstrap_key,authorization_id,approval_transaction_id,bootstrap_correlation_id,
               control_tenant_id,requester_actor_id,reviewer_actor_id,reviewer_user_id,
               created_user_id,created_actor_id,role,outcome,consumed_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "staging-first-privileged-identity-v1", current.authorization_id,
                current.approval_transaction_id, correlation_id, current.control_tenant_id,
                current.requester_actor_id, current.reviewer_actor_id, current.reviewer_user_id,
                int(created_user_id), str(created_actor_id), BOOTSTRAP_ROLE, "success", now.isoformat(),
            ),
        )
        return self.get(authorization_id, connection=connection)


__all__ = [
    "APPROVE_CAPABILITY", "BOOTSTRAP_ENVIRONMENT", "BOOTSTRAP_OPERATION",
    "BOOTSTRAP_PURPOSE", "BOOTSTRAP_ROLE", "BootstrapAuthorization",
    "StagingBootstrapAuthorizationError", "StagingBootstrapAuthorizationService",
    "VerifiedBootstrapPrincipal", "artifact_hash", "canonical_artifact",
]
