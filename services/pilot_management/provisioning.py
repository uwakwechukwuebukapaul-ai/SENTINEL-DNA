"""Bounded account and tenant provisioning for the remote analyst pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import secrets
import json
from typing import Any, Callable
from uuid import uuid4

from database.connection import DatabaseConnection, database
from database.portability import table_columns
from services.pilot_management.authorization import (
    PilotAuthorizationError,
    PilotAuthorizationService,
)


class PilotProvisioningError(ValueError):
    """Raised when a bounded pilot account operation is rejected."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise PilotProvisioningError(f"{field}_required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PilotProvisioningError(f"{field}_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise PilotProvisioningError(f"{field}_must_include_utc_offset")
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str, *, maximum: int = 256) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise PilotProvisioningError(f"{field}_required")
    if len(normalized) > maximum:
        raise PilotProvisioningError(f"{field}_too_long")
    return normalized


@dataclass(frozen=True)
class PilotAccountProvisioning:
    provisioning_id: str
    user_id: int
    analyst_id: str
    username: str
    email: str
    tenant_id: str
    manager_tenant_id: str
    authorization_id: str
    activation_id: str
    account_status: str
    authorization_status: str
    tenant_status: str
    created_at: str
    expires_at: str
    activation_expires_at: str
    approved_scenarios: tuple[str, ...]
    provisioned_by: str
    audit_correlation_id: str
    revoked_at: str | None = None
    revocation_reason: str | None = None
    activation_status: str = "pending"
    activation_token: str | None = None

    def to_dict(self, *, include_activation_token: bool = False) -> dict[str, Any]:
        result = asdict(self)
        result["approved_scenarios"] = list(self.approved_scenarios)
        result.pop("activation_token", None)
        if include_activation_token and self.activation_token is not None:
            result["activation_token"] = self.activation_token
        return result


class PilotAccountProvisioningService:
    """Atomically create and control one isolated analyst pilot account."""

    MAX_PILOT_DAYS = 30
    DEFAULT_ACTIVATION_HOURS = 24

    def __init__(
        self,
        db: DatabaseConnection | None = None,
        *,
        auth_service: Any,
        canonical_authority: Any,
        pilot_authorization_service: PilotAuthorizationService,
        audit_service: Any,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.db = db or database
        self.auth_service = auth_service
        self.canonical_authority = canonical_authority
        self.pilot_authorization_service = pilot_authorization_service
        self.audit_service = audit_service
        self.clock = clock
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pilot_tenants (
                    tenant_id TEXT PRIMARY KEY,
                    classification TEXT NOT NULL,
                    owner_actor_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    revoked_at TEXT,
                    revocation_reason TEXT,
                    audit_correlation_id TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pilot_account_provisioning (
                    provisioning_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    analyst_id TEXT NOT NULL UNIQUE,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    tenant_id TEXT NOT NULL UNIQUE,
                    manager_tenant_id TEXT NOT NULL,
                    authorization_id TEXT NOT NULL UNIQUE,
                    activation_id TEXT NOT NULL UNIQUE,
                    account_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approved_scenarios_json TEXT NOT NULL,
                    provisioned_by TEXT NOT NULL,
                    audit_correlation_id TEXT NOT NULL,
                    revoked_at TEXT,
                    revocation_reason TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pilot_account_activations (
                    activation_id TEXT PRIMARY KEY,
                    provisioning_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    consumed_at TEXT
                )
                """
            )
            columns = table_columns(
                connection, self.db.backend_name, "pilot_account_provisioning"
            )
            if "revoked_at" not in columns:
                connection.execute(
                    "ALTER TABLE pilot_account_provisioning ADD COLUMN revoked_at TEXT"
                )
            if "revocation_reason" not in columns:
                connection.execute(
                    "ALTER TABLE pilot_account_provisioning ADD COLUMN revocation_reason TEXT"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_pilot_tenants_status "
                "ON pilot_tenants(status, expires_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_pilot_accounts_manager_tenant "
                "ON pilot_account_provisioning(manager_tenant_id, created_at)"
            )

    def provision(
        self,
        *,
        manager_tenant_id: str,
        provisioned_by: str,
        username: str,
        email: str,
        display_name: str | None,
        tenant_name: str | None,
        expires_at: str,
        approved_scenarios: list[str] | tuple[str, ...],
        audit_correlation_id: str,
        activation_expires_at: str | None = None,
    ) -> PilotAccountProvisioning:
        manager_tenant_id = _text(manager_tenant_id, "manager_tenant_id")
        provisioned_by = _text(provisioned_by, "provisioned_by")
        username = _text(username, "username", maximum=128)
        email = _text(email, "email", maximum=320).lower()
        if "@" not in email:
            raise PilotProvisioningError("email_invalid")
        display_name = _text(display_name or username, "display_name", maximum=256)
        tenant_name = _text(
            tenant_name or "Sentinel DNA isolated analyst pilot",
            "tenant_name",
            maximum=128,
        )
        audit_correlation_id = _text(audit_correlation_id, "audit_correlation_id")
        now = self.clock().astimezone(timezone.utc)
        expiry = _parse_utc(expires_at, "expires_at")
        if expiry <= now:
            raise PilotProvisioningError("expires_at_must_be_future")
        if expiry > now + timedelta(days=self.MAX_PILOT_DAYS):
            raise PilotProvisioningError("expires_at_exceeds_pilot_limit")
        activation_expiry = (
            _parse_utc(activation_expires_at, "activation_expires_at")
            if activation_expires_at
            else min(expiry, now + timedelta(hours=self.DEFAULT_ACTIVATION_HOURS))
        )
        if activation_expiry <= now or activation_expiry > expiry:
            raise PilotProvisioningError("activation_expiry_invalid")

        scenarios = self.pilot_authorization_service._normalize_scenarios(
            approved_scenarios
        )
        tenant_id = f"pilot-tenant-{uuid4().hex}"
        analyst_id = f"pilot-analyst-{uuid4().hex}"
        provisioning_id = f"PILOT-ACCOUNT-{uuid4().hex}"
        authorization_id = f"PILOT-AUTH-{uuid4().hex}"
        activation_id = f"PILOT-ACT-{uuid4().hex}"
        activation_token = secrets.token_urlsafe(32)

        with self.db.session() as connection:
            self.pilot_authorization_service._validate_manager(
                provisioned_by,
                manager_tenant_id,
                "provisioned_by",
                connection=connection,
            )
            duplicate = connection.execute(
                "SELECT 1 FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=?",
                (username, email),
            ).fetchone()
            if duplicate:
                raise PilotProvisioningError("duplicate_account_identifier")

            self.canonical_authority.tenants.create(
                tenant_name, tenant_id=tenant_id, connection=connection
            )
            self.canonical_authority.memberships.add(
                tenant_id, provisioned_by, "soc_manager", connection=connection
            )
            self.canonical_authority.identities.create(
                email,
                display_name=display_name,
                actor_id=analyst_id,
                connection=connection,
            )
            self.canonical_authority.memberships.add(
                tenant_id, analyst_id, "analyst", connection=connection
            )
            user = self.auth_service.register(
                username,
                email,
                secrets.token_urlsafe(32),
                "analyst",
                tenant_id=tenant_id,
                actor_id=analyst_id,
                expires_at=expiry.isoformat(),
                revocation_status="pending",
                audit_correlation_id=audit_correlation_id,
                is_active=False,
                connection=connection,
            )
            connection.execute(
                """
                INSERT INTO pilot_tenants(
                    tenant_id, classification, owner_actor_id, started_at,
                    expires_at, status, audit_correlation_id
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    tenant_id,
                    "isolated_non_production_synthetic",
                    provisioned_by,
                    now.isoformat(),
                    expiry.isoformat(),
                    "active",
                    audit_correlation_id,
                ),
            )
            authorization = self.pilot_authorization_service.create(
                analyst_id=analyst_id,
                tenant_id=tenant_id,
                authorized_by=provisioned_by,
                expires_at=expiry.isoformat(),
                approved_scenarios=list(scenarios),
                    audit_correlation_id=audit_correlation_id,
                    connection=connection,
                    authorization_id=authorization_id,
                    allow_pending_analyst=True,
                )
            connection.execute(
                """
                INSERT INTO pilot_account_provisioning(
                    provisioning_id, user_id, analyst_id, username, email,
                    tenant_id, manager_tenant_id, authorization_id, activation_id,
                    account_status, created_at, expires_at,
                    approved_scenarios_json, provisioned_by, audit_correlation_id
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    provisioning_id,
                    user.id,
                    analyst_id,
                    username,
                    email,
                    tenant_id,
                    manager_tenant_id,
                    authorization.authorization_id,
                    activation_id,
                    "pending_activation",
                    now.isoformat(),
                    expiry.isoformat(),
                    json.dumps(list(scenarios), separators=(",", ":")),
                    provisioned_by,
                    audit_correlation_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO pilot_account_activations(
                    activation_id, provisioning_id, user_id, token_hash,
                    created_at, expires_at, status
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    activation_id,
                    provisioning_id,
                    user.id,
                    self.auth_service._hash_token(activation_token),
                    now.isoformat(),
                    activation_expiry.isoformat(),
                    "pending",
                ),
            )
            self._audit(
                "PILOT_TENANT_CREATED",
                tenant_id=tenant_id,
                actor_id=provisioned_by,
                correlation_id=audit_correlation_id,
                resource_type="pilot_tenant",
                resource_id=tenant_id,
                details={"classification": "isolated_non_production_synthetic"},
                connection=connection,
            )
            self._audit(
                "PILOT_ACCOUNT_PROVISIONED",
                tenant_id=tenant_id,
                actor_id=provisioned_by,
                correlation_id=audit_correlation_id,
                resource_type="pilot_account",
                resource_id=provisioning_id,
                details={
                    "user_id": user.id,
                    "analyst_id": analyst_id,
                    "authorization_id": authorization.authorization_id,
                    "activation_id": activation_id,
                    "account_status": "pending_activation",
                },
                connection=connection,
            )

        return PilotAccountProvisioning(
            provisioning_id=provisioning_id,
            user_id=user.id,
            analyst_id=analyst_id,
            username=username,
            email=email,
            tenant_id=tenant_id,
            manager_tenant_id=manager_tenant_id,
            authorization_id=authorization.authorization_id,
            activation_id=activation_id,
            account_status="pending_activation",
            authorization_status="active",
            tenant_status="active",
            created_at=now.isoformat(),
            expires_at=expiry.isoformat(),
            activation_expires_at=activation_expiry.isoformat(),
            approved_scenarios=scenarios,
            provisioned_by=provisioned_by,
            audit_correlation_id=audit_correlation_id,
            activation_token=activation_token,
        )

    def activate(
        self, *, token: str, password: str, audit_correlation_id: str
    ) -> PilotAccountProvisioning:
        token = _text(token, "activation_token", maximum=512)
        audit_correlation_id = _text(audit_correlation_id, "audit_correlation_id")
        password = str(password or "")
        if len(password) < 10:
            raise PilotProvisioningError("invalid_password")
        now = self.clock().astimezone(timezone.utc).isoformat()
        with self.db.session() as connection:
            row = connection.execute(
                """
                SELECT a.*, p.*, pt.status AS tenant_status,
                       p.audit_correlation_id AS provisioning_correlation_id
                FROM pilot_account_activations a
                JOIN pilot_account_provisioning p ON p.provisioning_id=a.provisioning_id
                JOIN pilot_tenants pt ON pt.tenant_id=p.tenant_id
                WHERE a.token_hash=? AND a.status='pending' AND a.expires_at>?
                  AND p.account_status='pending_activation'
                  AND pt.status='active' AND pt.expires_at>?
                """,
                (self.auth_service._hash_token(token), now, now),
            ).fetchone()
            if not row:
                raise PilotProvisioningError("activation_invalid")
            consumed = connection.execute(
                """
                UPDATE pilot_account_activations
                SET status='consumed', consumed_at=?
                WHERE activation_id=? AND status='pending' AND expires_at>?
                """,
                (now, row["activation_id"], now),
            )
            if consumed.rowcount != 1:
                raise PilotProvisioningError("activation_invalid")
            self.auth_service.reset_password(
                row["user_id"], password, connection=connection
            )
            if not self.auth_service.activate_user(row["user_id"], connection=connection):
                raise PilotProvisioningError("activation_invalid")
            connection.execute(
                "UPDATE pilot_account_provisioning SET account_status='active' WHERE provisioning_id=?",
                (row["provisioning_id"],),
            )
            self._audit(
                "PILOT_ANALYST_ACTIVATED",
                tenant_id=row["tenant_id"],
                actor_id=row["analyst_id"],
                correlation_id=audit_correlation_id,
                resource_type="pilot_account",
                resource_id=row["provisioning_id"],
                details={"activation_id": row["activation_id"], "account_status": "active"},
                connection=connection,
            )
        return self.get(row["provisioning_id"])

    def get(
        self, provisioning_id: str, *, manager_tenant_id: str | None = None
    ) -> PilotAccountProvisioning | None:
        provisioning_id = _text(provisioning_id, "provisioning_id")
        with self.db.session() as connection:
            row = connection.execute(
                """
                SELECT p.*, a.status AS activation_status,
                       a.expires_at AS activation_expires_at,
                       pa.authorization_status, pa.approved_scenarios_json,
                       pt.status AS tenant_status
                FROM pilot_account_provisioning p
                JOIN pilot_account_activations a ON a.activation_id=p.activation_id
                JOIN pilot_authorizations pa ON pa.authorization_id=p.authorization_id
                JOIN pilot_tenants pt ON pt.tenant_id=p.tenant_id
                WHERE p.provisioning_id=?
                """,
                (provisioning_id,),
            ).fetchone()
        if not row:
            return None
        if manager_tenant_id is not None and row["manager_tenant_id"] != str(manager_tenant_id):
            return None
        return self._from_row(row)

    def list_for_manager(self, manager_tenant_id: str) -> list[PilotAccountProvisioning]:
        manager_tenant_id = _text(manager_tenant_id, "manager_tenant_id")
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT provisioning_id FROM pilot_account_provisioning "
                "WHERE manager_tenant_id=? ORDER BY created_at DESC, provisioning_id DESC",
                (manager_tenant_id,),
            ).fetchall()
        return [item for row in rows if (item := self.get(row["provisioning_id"]))]

    def revoke(
        self,
        *,
        provisioning_id: str,
        manager_tenant_id: str,
        revoked_by: str,
        reason: str,
        audit_correlation_id: str,
    ) -> PilotAccountProvisioning:
        provisioning_id = _text(provisioning_id, "provisioning_id")
        manager_tenant_id = _text(manager_tenant_id, "manager_tenant_id")
        revoked_by = _text(revoked_by, "revoked_by")
        reason = _text(reason, "revocation_reason", maximum=512)
        audit_correlation_id = _text(audit_correlation_id, "audit_correlation_id")
        now = self.clock().astimezone(timezone.utc).isoformat()
        with self.db.session() as connection:
            self.pilot_authorization_service._validate_manager(
                revoked_by,
                manager_tenant_id,
                "revoked_by",
                connection=connection,
            )
            row = connection.execute(
                "SELECT * FROM pilot_account_provisioning WHERE provisioning_id=? AND manager_tenant_id=?",
                (provisioning_id, manager_tenant_id),
            ).fetchone()
            if not row:
                raise PilotProvisioningError("pilot_account_not_found")
            if row["account_status"] == "revoked":
                raise PilotProvisioningError("pilot_account_not_active")
            self.pilot_authorization_service.revoke(
                row["authorization_id"],
                tenant_id=row["tenant_id"],
                revoked_by=revoked_by,
                reason=reason,
                audit_correlation_id=audit_correlation_id,
                connection=connection,
            )
            self.auth_service.deactivate_user(row["user_id"], connection=connection)
            connection.execute(
                """
                UPDATE users SET is_active=0, revocation_status='revoked',
                    session_version=COALESCE(session_version, 0)+1
                WHERE id=?
                """,
                (row["user_id"],),
            )
            self.auth_service.revoke_all_sessions(row["user_id"], connection=connection)
            self.canonical_authority.tenants.set_status(
                row["tenant_id"], "inactive", connection=connection
            )
            connection.execute(
                "UPDATE pilot_tenants SET status='revoked', revoked_at=?, revocation_reason=? WHERE tenant_id=?",
                (now, reason, row["tenant_id"]),
            )
            connection.execute(
                "UPDATE pilot_account_activations SET status='revoked' WHERE activation_id=? AND status='pending'",
                (row["activation_id"],),
            )
            connection.execute(
                """
                UPDATE pilot_account_provisioning
                SET account_status='revoked', revoked_at=?, revocation_reason=?
                WHERE provisioning_id=? AND account_status<>'revoked'
                """,
                (now, reason, provisioning_id),
            )
            self._audit(
                "PILOT_ACCOUNT_DEACTIVATED",
                tenant_id=row["tenant_id"],
                actor_id=revoked_by,
                correlation_id=audit_correlation_id,
                resource_type="pilot_account",
                resource_id=provisioning_id,
                details={"analyst_id": row["analyst_id"], "sessions_revoked": True},
                connection=connection,
            )
            self._audit(
                "PILOT_TENANT_REVOKED",
                tenant_id=row["tenant_id"],
                actor_id=revoked_by,
                correlation_id=audit_correlation_id,
                resource_type="pilot_tenant",
                resource_id=row["tenant_id"],
                details={"reason": reason},
                connection=connection,
            )
        return self.get(provisioning_id, manager_tenant_id=manager_tenant_id)

    def _from_row(self, row: Any) -> PilotAccountProvisioning:
        return PilotAccountProvisioning(
            provisioning_id=str(row["provisioning_id"]),
            user_id=int(row["user_id"]),
            analyst_id=str(row["analyst_id"]),
            username=str(row["username"]),
            email=str(row["email"]),
            tenant_id=str(row["tenant_id"]),
            manager_tenant_id=str(row["manager_tenant_id"]),
            authorization_id=str(row["authorization_id"]),
            activation_id=str(row["activation_id"]),
            account_status=str(row["account_status"]),
            authorization_status=str(row["authorization_status"]),
            tenant_status=str(row["tenant_status"]),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]),
            activation_expires_at=str(row["activation_expires_at"]),
            approved_scenarios=tuple(json.loads(row["approved_scenarios_json"])),
            provisioned_by=str(row["provisioned_by"]),
            audit_correlation_id=str(row["audit_correlation_id"]),
            revoked_at=row["revoked_at"],
            revocation_reason=row["revocation_reason"],
            activation_status=str(row["activation_status"]),
        )

    def _audit(self, event_type: str, *, connection: Any, **kwargs: Any) -> None:
        self.audit_service.record(event_type, connection=connection, **kwargs)


__all__ = [
    "PilotAccountProvisioning",
    "PilotAccountProvisioningService",
    "PilotProvisioningError",
]
