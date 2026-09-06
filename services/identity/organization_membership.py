"""Canonical organization-domain and membership lifecycle boundary.

This is an additive extension of the existing canonical authority.  It does not
create a second user, tenant, workspace, RBAC, session, or audit system.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from database.connection import DatabaseConnection, database
from database.portability import integrity_error, table_columns
from services.auth.onboarding import OnboardingState


class OrganizationMembershipError(ValueError):
    """Safe category for organization and membership failures."""


POLICIES = frozenset({
    "INVITATION_REQUIRED",
    "ADMIN_APPROVAL_REQUIRED",
    "VERIFIED_DOMAIN_AUTO_JOIN",
    "SSO_REQUIRED",
    "DISABLED",
})
DOMAIN_STATES = frozenset({"unverified", "verified", "expired", "revoked"})
MEMBERSHIP_STATES = frozenset({"invited", "pending", "active", "suspended", "revoked", "declined", "expired"})
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def normalize_email(value: str) -> str:
    email = str(value or "").strip().casefold()
    if email.count("@") != 1 or len(email) > 320:
        raise OrganizationMembershipError("invalid_email")
    local, domain = email.rsplit("@", 1)
    if not local or not domain:
        raise OrganizationMembershipError("invalid_email")
    return f"{local}@{normalize_domain(domain)}"


def normalize_domain(value: str) -> str:
    domain = str(value or "").strip().casefold().rstrip(".")
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise OrganizationMembershipError("invalid_domain") from exc
    if not _DOMAIN_RE.fullmatch(domain):
        raise OrganizationMembershipError("invalid_domain")
    return domain


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OrganizationDecision:
    domain: str
    tenant_id: str | None
    tenant_status: str | None
    verification_status: str | None
    enrollment_policy: str | None

    @property
    def existing_verified_active(self) -> bool:
        return self.verification_status == "verified" and self.tenant_status == "active" and bool(self.tenant_id)


class OrganizationMembershipService:
    """Own organization enrollment records while delegating authorization."""

    def __init__(self, db: DatabaseConnection = database, *, authority=None, auth=None, audit=None):
        self.db, self.authority, self.auth, self.audit = db, authority, auth, audit
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            from database.canonical_authority import ensure_canonical_schema
            ensure_canonical_schema(connection, commit=False)
            connection.execute(
                """CREATE TABLE IF NOT EXISTS canonical_organization_domains (
                    domain TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    enrollment_policy TEXT NOT NULL,
                    verified_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES canonical_tenants(tenant_id)
                )"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_org_domains_tenant ON canonical_organization_domains(tenant_id)")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS canonical_membership_requests (
                    request_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    requested_email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    decided_at TEXT,
                    decided_by TEXT,
                    FOREIGN KEY (tenant_id) REFERENCES canonical_tenants(tenant_id)
                )"""
            )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_membership_request "
                "ON canonical_membership_requests(tenant_id, actor_id) WHERE status='pending'"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_membership_requests_tenant ON canonical_membership_requests(tenant_id, status, created_at)")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS canonical_membership_invitations (
                    invitation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    invited_email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    accepted_at TEXT,
                    accepted_by INTEGER,
                    FOREIGN KEY (tenant_id) REFERENCES canonical_tenants(tenant_id)
                )"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_invitations_email ON canonical_membership_invitations(invited_email, status, expires_at)")
            columns = table_columns(connection, self.db.backend_name, "canonical_memberships")
            if "lifecycle_state" not in columns:
                connection.execute("ALTER TABLE canonical_memberships ADD COLUMN lifecycle_state TEXT NOT NULL DEFAULT 'active'")

    def inspect_email(self, email: str, *, connection=None) -> OrganizationDecision:
        normalized = normalize_email(email)
        domain = normalized.rsplit("@", 1)[1]

        def read(conn):
            row = conn.execute(
                """SELECT d.domain, d.tenant_id, t.status AS tenant_status,
                          d.verification_status, d.enrollment_policy
                     FROM canonical_organization_domains d
                     JOIN canonical_tenants t ON t.tenant_id=d.tenant_id
                    WHERE d.domain=?""",
                (domain,),
            ).fetchone()
            if not row:
                return OrganizationDecision(domain, None, None, None, None)
            return OrganizationDecision(domain, row["tenant_id"], row["tenant_status"], row["verification_status"], row["enrollment_policy"])

        if connection is not None:
            return read(connection)
        with self.db.session() as conn:
            return read(conn)

    def configure_domain(self, context, domain: str, *, tenant_id: str | None = None, verification_status: str = "verified", enrollment_policy: str = "ADMIN_APPROVAL_REQUIRED") -> dict[str, Any]:
        domain = normalize_domain(domain)
        if verification_status not in DOMAIN_STATES or enrollment_policy not in POLICIES:
            raise OrganizationMembershipError("invalid_domain_policy")
        tenant_id = str(tenant_id or getattr(context, "tenant_id", "") or "")
        actor_id = str(getattr(context, "actor_id", "") or "")
        self._require_admin(context, tenant_id)
        now = _now()
        with self.db.session() as connection:
            existing = connection.execute("SELECT tenant_id FROM canonical_organization_domains WHERE domain=?", (domain,)).fetchone()
            if existing and str(existing["tenant_id"]) != tenant_id:
                raise OrganizationMembershipError("domain_ownership_conflict")
            connection.execute(
                """INSERT INTO canonical_organization_domains(domain, tenant_id, verification_status, enrollment_policy, verified_at, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(domain) DO UPDATE SET verification_status=excluded.verification_status,
                     enrollment_policy=excluded.enrollment_policy, verified_at=excluded.verified_at,
                     updated_at=excluded.updated_at""",
                (domain, tenant_id, verification_status, enrollment_policy, now if verification_status == "verified" else None, now, now),
            )
            self._audit("ORGANIZATION_DOMAIN_CONFIGURED", tenant_id, actor_id, {"domain": domain, "verification_status": verification_status, "enrollment_policy": enrollment_policy}, connection)
        return {"domain": domain, "tenant_id": tenant_id, "verification_status": verification_status, "enrollment_policy": enrollment_policy}

    def ensure_user_identity(self, user_id: int, *, connection=None) -> str:
        def ensure(conn):
            user = conn.execute("SELECT id, email, actor_id FROM users WHERE id=?", (user_id,)).fetchone()
            if not user:
                raise OrganizationMembershipError("identity_not_found")
            email = normalize_email(user["email"])
            existing = conn.execute("SELECT actor_id FROM canonical_identities WHERE email=?", (email,)).fetchone()
            actor_id = str(user["actor_id"] or (existing["actor_id"] if existing else f"user-{user_id}"))
            if existing and str(existing["actor_id"]) != actor_id:
                raise OrganizationMembershipError("identity_binding_conflict")
            if not existing:
                now = _now()
                conn.execute(
                    "INSERT INTO canonical_identities(actor_id,email,display_name,status,created_at,updated_at) VALUES(?,?,?,'active',?,?)",
                    (actor_id, email, "", now, now),
                )
            conn.execute("UPDATE users SET actor_id=? WHERE id=?", (actor_id, user_id))
            return actor_id

        if connection is not None:
            return ensure(connection)
        with self.db.session() as conn:
            return ensure(conn)

    def create_join_request(self, user_id: int, tenant_id: str, *, connection=None) -> dict[str, Any]:
        def create(conn):
            actor_id = self.ensure_user_identity(user_id, connection=conn)
            user = conn.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
            existing = conn.execute(
                "SELECT * FROM canonical_membership_requests WHERE tenant_id=? AND actor_id=? AND status='pending'",
                (tenant_id, actor_id),
            ).fetchone()
            if existing:
                return dict(existing)
            now = _now()
            request_id = str(uuid4())
            try:
                conn.execute(
                    """INSERT INTO canonical_membership_requests(request_id,tenant_id,actor_id,user_id,requested_email,status,created_at,updated_at)
                       VALUES(?,?,?,?,?,'pending',?,?)""",
                    (request_id, tenant_id, actor_id, user_id, normalize_email(user["email"]), now, now),
                )
            except Exception as exc:
                if not integrity_error(exc):
                    raise
                row = conn.execute("SELECT * FROM canonical_membership_requests WHERE tenant_id=? AND actor_id=? AND status='pending'", (tenant_id, actor_id)).fetchone()
                if row:
                    return dict(row)
                raise OrganizationMembershipError("join_request_unavailable") from exc
            self._audit("ORGANIZATION_JOIN_REQUESTED", tenant_id, actor_id, {"request_id": request_id}, conn)
            return dict(conn.execute("SELECT * FROM canonical_membership_requests WHERE request_id=?", (request_id,)).fetchone())

        if connection is not None:
            return create(connection)
        with self.db.session() as conn:
            return create(conn)

    def auto_join_user(self, user_id: int, tenant_id: str) -> dict[str, Any]:
        """Join only an explicitly verified, active auto-join domain."""
        with self.db.session() as connection:
            decision = self.inspect_email(
                connection.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()["email"],
                connection=connection,
            )
            if (
                not decision.existing_verified_active
                or decision.tenant_id != str(tenant_id)
                or decision.enrollment_policy != "VERIFIED_DOMAIN_AUTO_JOIN"
            ):
                raise OrganizationMembershipError("organization_auto_join_denied")
            actor_id = self.ensure_user_identity(user_id, connection=connection)
            now = _now()
            connection.execute(
                """INSERT INTO canonical_memberships(tenant_id,actor_id,role,status,lifecycle_state,created_at,updated_at)
                   VALUES(?,?, 'analyst','active','active',?,?)
                   ON CONFLICT(tenant_id,actor_id) DO UPDATE SET role='analyst',status='active',lifecycle_state='active',updated_at=excluded.updated_at""",
                (tenant_id, actor_id, now, now),
            )
            connection.execute("UPDATE users SET tenant_id=? WHERE id=?", (tenant_id, user_id))
            self._audit("MEMBERSHIP_CREATED", str(tenant_id), actor_id, {"source": "verified_domain_auto_join"}, connection)
            return {"tenant_id": str(tenant_id), "actor_id": actor_id, "membership_status": "active"}

    def create_invitation(self, context, email: str, *, ttl_hours: int = 72) -> dict[str, Any]:
        tenant_id = str(getattr(context, "tenant_id", "") or "")
        actor_id = str(getattr(context, "actor_id", "") or "")
        self._require_admin(context, tenant_id)
        if ttl_hours < 1 or ttl_hours > 168:
            raise OrganizationMembershipError("invalid_invitation_expiry")
        invited_email = normalize_email(email)
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        invitation_id = str(uuid4())
        with self.db.session() as connection:
            connection.execute(
                """INSERT INTO canonical_membership_invitations(invitation_id,tenant_id,invited_email,role,token_hash,status,expires_at,created_at)
                   VALUES(?,?,?,'analyst',?,'invited',?,?)""",
                (invitation_id, tenant_id, invited_email, _token_hash(token), (now + timedelta(hours=ttl_hours)).isoformat(), now.isoformat()),
            )
            self._audit("ORGANIZATION_INVITATION_CREATED", tenant_id, actor_id, {"invitation_id": invitation_id, "invited_email": invited_email}, connection)
        return {"invitation_id": invitation_id, "token": token, "expires_at": (now + timedelta(hours=ttl_hours)).isoformat()}

    def accept_invitation(self, user_id: int, token: str) -> dict[str, Any]:
        if not str(token or "").strip():
            raise OrganizationMembershipError("invitation_invalid")
        now = _now()
        with self.db.session() as connection:
            user = connection.execute("SELECT id,email FROM users WHERE id=? AND is_active=1", (user_id,)).fetchone()
            if not user:
                raise OrganizationMembershipError("invitation_invalid")
            row = connection.execute(
                """SELECT i.* , t.status AS tenant_status FROM canonical_membership_invitations i
                     JOIN canonical_tenants t ON t.tenant_id=i.tenant_id
                    WHERE i.token_hash=? AND i.status='invited' AND i.expires_at>?""",
                (_token_hash(token), now),
            ).fetchone()
            if not row or row["tenant_status"] != "active" or normalize_email(user["email"]) != row["invited_email"]:
                raise OrganizationMembershipError("invitation_invalid")
            actor_id = self.ensure_user_identity(user_id, connection=connection)
            consumed = connection.execute(
                "UPDATE canonical_membership_invitations SET status='accepted', accepted_at=?, accepted_by=? WHERE invitation_id=? AND status='invited' AND expires_at>?",
                (now, user_id, row["invitation_id"], now),
            )
            if consumed.rowcount != 1:
                raise OrganizationMembershipError("invitation_invalid")
            connection.execute(
                """INSERT INTO canonical_memberships(tenant_id,actor_id,role,status,lifecycle_state,created_at,updated_at)
                   VALUES(?,?,?,'active','active',?,?)
                   ON CONFLICT(tenant_id,actor_id) DO UPDATE SET role=excluded.role,status='active',lifecycle_state='active',updated_at=excluded.updated_at""",
                (row["tenant_id"], actor_id, row["role"], now, now),
            )
            if self.auth:
                current = connection.execute("SELECT onboarding_state FROM users WHERE id=?", (user_id,)).fetchone()
                if current and current["onboarding_state"] == OnboardingState.ORGANIZATION_MEMBERSHIP_PENDING:
                    self.auth.transition_onboarding(user_id, OnboardingState.ORGANIZATION_MEMBERSHIP_APPROVED, connection=connection)
                connection.execute("UPDATE users SET tenant_id=? WHERE id=?", (row["tenant_id"], user_id))
            self._audit("INVITATION_ACCEPTED", row["tenant_id"], actor_id, {"invitation_id": row["invitation_id"]}, connection)
            return {"tenant_id": row["tenant_id"], "actor_id": actor_id, "membership_status": "active", "onboarding_state": OnboardingState.ORGANIZATION_MEMBERSHIP_APPROVED}

    def decide_join_request(self, context, request_id: str, *, approve: bool) -> dict[str, Any]:
        tenant_id = str(getattr(context, "tenant_id", "") or "")
        actor_id = str(getattr(context, "actor_id", "") or "")
        self._require_admin(context, tenant_id)
        now = _now()
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM canonical_membership_requests WHERE request_id=? AND tenant_id=? AND status='pending'", (request_id, tenant_id)).fetchone()
            if not row:
                raise OrganizationMembershipError("join_request_not_found")
            next_status = "approved" if approve else "denied"
            connection.execute("UPDATE canonical_membership_requests SET status=?,updated_at=?,decided_at=?,decided_by=? WHERE request_id=? AND status='pending'", (next_status, now, now, actor_id, request_id))
            if approve:
                connection.execute(
                    """INSERT INTO canonical_memberships(tenant_id,actor_id,role,status,lifecycle_state,created_at,updated_at)
                       VALUES(?,?, 'analyst','active','active',?,?)
                       ON CONFLICT(tenant_id,actor_id) DO UPDATE SET role='analyst',status='active',lifecycle_state='active',updated_at=excluded.updated_at""",
                    (tenant_id, row["actor_id"], now, now),
                )
                connection.execute("UPDATE users SET tenant_id=? WHERE id=?", (tenant_id, row["user_id"]))
                if self.auth:
                    current = connection.execute("SELECT onboarding_state FROM users WHERE id=?", (row["user_id"],)).fetchone()
                    if current and current["onboarding_state"] == OnboardingState.ORGANIZATION_MEMBERSHIP_PENDING:
                        self.auth.transition_onboarding(row["user_id"], OnboardingState.ORGANIZATION_MEMBERSHIP_APPROVED, connection=connection)
            self._audit("ORGANIZATION_JOIN_APPROVED" if approve else "ORGANIZATION_JOIN_DENIED", tenant_id, actor_id, {"request_id": request_id}, connection)
            return {"request_id": request_id, "status": next_status}

    def revoke_membership(self, context, *, actor_id: str, user_id: int, tenant_id: str, reason: str = "") -> None:
        tenant_id, acting_actor = str(tenant_id), str(getattr(context, "actor_id", "") or "")
        self._require_admin(context, tenant_id)
        now = _now()
        with self.db.session() as connection:
            membership = connection.execute("SELECT * FROM canonical_memberships WHERE tenant_id=? AND actor_id=?", (tenant_id, actor_id)).fetchone()
            if not membership:
                raise OrganizationMembershipError("membership_not_found")
            connection.execute("UPDATE canonical_memberships SET status='inactive', lifecycle_state='revoked', updated_at=? WHERE tenant_id=? AND actor_id=?", (now, tenant_id, actor_id))
            remaining = connection.execute("SELECT tenant_id FROM canonical_memberships WHERE actor_id=? AND status='active' AND lifecycle_state='active' ORDER BY tenant_id", (actor_id,)).fetchall()
            if self.auth:
                self.auth.invalidate_user_sessions(user_id, connection=connection)
            if remaining:
                connection.execute("UPDATE users SET tenant_id=? WHERE id=?", (remaining[0]["tenant_id"], user_id))
            else:
                connection.execute("UPDATE users SET tenant_id=NULL WHERE id=?", (user_id,))
                if self.auth:
                    current = connection.execute("SELECT onboarding_state FROM users WHERE id=?", (user_id,)).fetchone()
                    if current and current["onboarding_state"] == OnboardingState.AUTHENTICATED:
                        self.auth.transition_onboarding(user_id, OnboardingState.ORGANIZATION_MEMBERSHIP_PENDING, connection=connection)
            self._audit("MEMBERSHIP_REVOKED", tenant_id, acting_actor, {"subject_actor_id": actor_id, "reason": str(reason or "")[:256]}, connection)

    def _require_admin(self, context, tenant_id: str) -> None:
        actor_id = str(getattr(context, "actor_id", "") or "")
        if not actor_id or not tenant_id or str(getattr(context, "tenant_id", "") or "") != tenant_id:
            raise OrganizationMembershipError("organization_authorization_denied")
        try:
            _tenant, _identity, membership = self.authority.resolve(tenant_id, actor_id)
        except Exception as exc:
            raise OrganizationMembershipError("organization_authorization_denied") from exc
        if membership.role not in {"admin", "soc_manager"} or membership.lifecycle_state != "active":
            raise OrganizationMembershipError("organization_authorization_denied")

    def _audit(self, event: str, tenant_id: str, actor_id: str, details: dict[str, Any], connection: Any) -> None:
        if self.audit:
            self.audit.record(event, tenant_id=tenant_id, actor_id=actor_id, details=details, connection=connection, outcome="success")


__all__ = [
    "DOMAIN_STATES", "MEMBERSHIP_STATES", "POLICIES", "OrganizationDecision",
    "OrganizationMembershipError", "OrganizationMembershipService", "normalize_domain", "normalize_email",
]
