"""Durable, tenant-scoped authorization for a bounded analyst pilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any, Callable, Mapping
from uuid import uuid4

from database.connection import DatabaseConnection, database
from database.portability import table_columns


class PilotAuthorizationError(ValueError):
    """Raised when a pilot authorization request cannot be accepted."""


# These identifiers are drawn from the repository's existing deterministic
# evaluation/demo fixtures.  A scenario not represented here must be added to
# the approved fixture catalog before it can be authorized.
APPROVED_SCENARIOS = frozenset(
    {
        "phishing_compromise",
        "credential_theft",
        "malware_execution",
        "suspicious_authentication",
        "lateral_movement",
        "command_and_control",
        "benign_false_positive",
        "multi_ioc_investigation",
        "suspicious_powershell_execution",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise PilotAuthorizationError(f"{field}_required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PilotAuthorizationError(f"{field}_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise PilotAuthorizationError(f"{field}_must_include_utc_offset")
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str, *, maximum: int = 256) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise PilotAuthorizationError(f"{field}_required")
    if len(normalized) > maximum:
        raise PilotAuthorizationError(f"{field}_too_long")
    return normalized


@dataclass(frozen=True)
class PilotAuthorization:
    authorization_id: str
    analyst_id: str
    tenant_id: str
    role: str
    authorization_status: str
    authorized_by: str
    authorized_at: str
    expires_at: str
    approved_scenarios: tuple[str, ...]
    revocation_status: str
    revoked_at: str | None
    revocation_reason: str | None
    audit_correlation_id: str

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["approved_scenarios"] = list(self.approved_scenarios)
        return result


class PilotAuthorizationService:
    """Persist and evaluate one bounded analyst authorization boundary."""

    def __init__(
        self,
        db: DatabaseConnection | None = None,
        *,
        auth_service: Any | None = None,
        canonical_authority: Any | None = None,
        audit_service: Any | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.db = db or database
        self.auth_service = auth_service
        self.canonical_authority = canonical_authority
        self.audit_service = audit_service
        self.clock = clock
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pilot_authorizations (
                    authorization_id TEXT PRIMARY KEY,
                    analyst_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    authorization_status TEXT NOT NULL,
                    authorized_by TEXT NOT NULL,
                    authorized_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approved_scenarios_json TEXT NOT NULL,
                    revocation_status TEXT NOT NULL,
                    revoked_at TEXT,
                    revocation_reason TEXT,
                    audit_correlation_id TEXT NOT NULL
                )
                """
            )
            columns = table_columns(
                connection, self.db.backend_name, "pilot_authorizations"
            )
            # This keeps a future pre-existing table safe if the service is
            # introduced after an early pilot database was initialized.
            migrations = {
                "revocation_status": "ALTER TABLE pilot_authorizations ADD COLUMN revocation_status TEXT NOT NULL DEFAULT 'not_revoked'",
                "revoked_at": "ALTER TABLE pilot_authorizations ADD COLUMN revoked_at TEXT",
                "revocation_reason": "ALTER TABLE pilot_authorizations ADD COLUMN revocation_reason TEXT",
                "audit_correlation_id": "ALTER TABLE pilot_authorizations ADD COLUMN audit_correlation_id TEXT NOT NULL DEFAULT ''",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_pilot_auth_tenant_status "
                "ON pilot_authorizations(tenant_id, authorization_status, expires_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_pilot_auth_analyst_tenant "
                "ON pilot_authorizations(analyst_id, tenant_id, authorization_status)"
            )

    def create(
        self,
        *,
        analyst_id: str,
        tenant_id: str,
        authorized_by: str,
        expires_at: str,
        approved_scenarios: list[str] | tuple[str, ...],
        audit_correlation_id: str,
        connection: Any | None = None,
        authorization_id: str | None = None,
        allow_pending_analyst: bool = False,
    ) -> PilotAuthorization:
        analyst_id = _text(analyst_id, "analyst_id")
        tenant_id = _text(tenant_id, "tenant_id")
        authorized_by = _text(authorized_by, "authorized_by")
        audit_correlation_id = _text(audit_correlation_id, "audit_correlation_id")
        expiry = _parse_utc(expires_at, "expires_at")
        now = self.clock().astimezone(timezone.utc)
        if expiry <= now:
            raise PilotAuthorizationError("expires_at_must_be_future")
        scenarios = self._normalize_scenarios(approved_scenarios)
        self._validate_analyst(
            analyst_id,
            tenant_id,
            connection=connection,
            allow_pending=allow_pending_analyst,
        )
        self._validate_manager(authorized_by, tenant_id, "authorized_by", connection=connection)
        authorization = PilotAuthorization(
            authorization_id=authorization_id or f"PILOT-AUTH-{uuid4().hex}",
            analyst_id=analyst_id,
            tenant_id=tenant_id,
            role="analyst",
            authorization_status="active",
            authorized_by=authorized_by,
            authorized_at=now.isoformat(),
            expires_at=expiry.isoformat(),
            approved_scenarios=scenarios,
            revocation_status="not_revoked",
            revoked_at=None,
            revocation_reason=None,
            audit_correlation_id=audit_correlation_id,
        )
        def insert(owned_connection):
            owned_connection.execute(
                """
                INSERT INTO pilot_authorizations(
                    authorization_id, analyst_id, tenant_id, role,
                    authorization_status, authorized_by, authorized_at,
                    expires_at, approved_scenarios_json, revocation_status,
                    revoked_at, revocation_reason, audit_correlation_id
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    authorization.authorization_id,
                    authorization.analyst_id,
                    authorization.tenant_id,
                    authorization.role,
                    authorization.authorization_status,
                    authorization.authorized_by,
                    authorization.authorized_at,
                    authorization.expires_at,
                    json.dumps(list(authorization.approved_scenarios), separators=(",", ":")),
                    authorization.revocation_status,
                    authorization.revoked_at,
                    authorization.revocation_reason,
                    authorization.audit_correlation_id,
                ),
            )
            self._audit(
                "PILOT_AUTHORIZATION_CREATED",
                authorization,
                connection=owned_connection,
                actor_id=authorized_by,
            )
        if connection is None:
            with self.db.session() as owned_connection:
                insert(owned_connection)
        else:
            insert(connection)
        return authorization

    def get(self, authorization_id: str, *, tenant_id: str | None = None, connection: Any | None = None) -> PilotAuthorization | None:
        authorization_id = _text(authorization_id, "authorization_id")
        def fetch(owned_connection):
            return owned_connection.execute(
                "SELECT * FROM pilot_authorizations WHERE authorization_id=?",
                (authorization_id,),
            ).fetchone()
        if connection is None:
            with self.db.session() as owned_connection:
                row = fetch(owned_connection)
        else:
            row = fetch(connection)
        if not row:
            return None
        result = self._from_row(row)
        if tenant_id is not None and result.tenant_id != str(tenant_id):
            return None
        return result

    def list_for_tenant(self, tenant_id: str) -> list[PilotAuthorization]:
        tenant_id = _text(tenant_id, "tenant_id")
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM pilot_authorizations WHERE tenant_id=? "
                "ORDER BY authorized_at DESC, authorization_id DESC",
                (tenant_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def active_for(self, analyst_id: str, tenant_id: str) -> PilotAuthorization | None:
        analyst_id = _text(analyst_id, "analyst_id")
        tenant_id = _text(tenant_id, "tenant_id")
        now = self.clock().astimezone(timezone.utc).isoformat()
        # Test/application harnesses may replace the configured database
        # backend after the container is built.  Re-asserting this idempotent
        # table boundary keeps authorization fail-closed without treating a
        # missing table as an authorization success.
        self._ensure_table_exists()
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM pilot_authorizations "
                "WHERE analyst_id=? AND tenant_id=? AND authorization_status='active' "
                "AND expires_at>? ORDER BY authorized_at DESC, authorization_id DESC",
                (analyst_id, tenant_id, now),
            ).fetchall()
        # Ambiguity is denied rather than selecting an arbitrary authorization.
        if len(rows) != 1:
            return None
        return self._from_row(rows[0])

    def _ensure_table_exists(self, connection: Any | None = None) -> None:
        def ensure(owned_connection):
            owned_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pilot_authorizations (
                    authorization_id TEXT PRIMARY KEY,
                    analyst_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    authorization_status TEXT NOT NULL,
                    authorized_by TEXT NOT NULL,
                    authorized_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approved_scenarios_json TEXT NOT NULL,
                    revocation_status TEXT NOT NULL,
                    revoked_at TEXT,
                    revocation_reason TEXT,
                    audit_correlation_id TEXT NOT NULL
                )
                """
            )
        if connection is None:
            with self.db.session() as owned_connection:
                ensure(owned_connection)
        else:
            ensure(connection)

    def is_scenario_allowed(self, authorization_id: str, scenario_id: str, *, tenant_id: str) -> bool:
        authorization = self.get(authorization_id, tenant_id=tenant_id)
        return bool(
            authorization
            and authorization.authorization_status == "active"
            and authorization.expires_at > self.clock().astimezone(timezone.utc).isoformat()
            and str(scenario_id or "").strip() in authorization.approved_scenarios
        )

    def revoke(
        self,
        authorization_id: str,
        *,
        tenant_id: str,
        revoked_by: str,
        reason: str,
        audit_correlation_id: str,
        connection: Any | None = None,
    ) -> PilotAuthorization:
        revoked_by = _text(revoked_by, "revoked_by")
        reason = _text(reason, "revocation_reason", maximum=512)
        audit_correlation_id = _text(audit_correlation_id, "audit_correlation_id")
        if connection is None:
            with self.db.session() as owned_connection:
                return self.revoke(
                    authorization_id,
                    tenant_id=tenant_id,
                    revoked_by=revoked_by,
                    reason=reason,
                    audit_correlation_id=audit_correlation_id,
                    connection=owned_connection,
                )
        self._validate_manager(revoked_by, tenant_id, "revoked_by", connection=connection)
        existing = self.get(authorization_id, tenant_id=tenant_id, connection=connection)
        if existing is None:
            raise PilotAuthorizationError("pilot_authorization_not_found")
        if existing.authorization_status != "active":
            raise PilotAuthorizationError("pilot_authorization_not_active")
        now = self.clock().astimezone(timezone.utc).isoformat()
        cursor = connection.execute(
                """
                UPDATE pilot_authorizations
                SET authorization_status='revoked', revocation_status='revoked',
                    revoked_at=?, revocation_reason=?, audit_correlation_id=?
                WHERE authorization_id=? AND tenant_id=? AND authorization_status='active'
                """,
                (now, reason, audit_correlation_id, authorization_id, tenant_id),
            )
        if cursor.rowcount != 1:
            raise PilotAuthorizationError("pilot_authorization_not_active")
        self._invalidate_sessions(existing.analyst_id, connection=connection)
        revoked = PilotAuthorization(
            **{
                **existing.to_dict(),
                "approved_scenarios": existing.approved_scenarios,
                "authorization_status": "revoked",
                "revocation_status": "revoked",
                "revoked_at": now,
                "revocation_reason": reason,
                "audit_correlation_id": audit_correlation_id,
            }
        )
        self._audit(
            "PILOT_AUTHORIZATION_REVOKED",
            revoked,
            connection=connection,
            actor_id=revoked_by,
            details={"reason": reason, "sessions_revoked": True},
        )
        return revoked

    def _validate_analyst(
        self,
        analyst_id: str,
        tenant_id: str,
        *,
        connection: Any | None = None,
        allow_pending: bool = False,
    ) -> None:
        if self.canonical_authority is None:
            raise PilotAuthorizationError("canonical_authority_required")
        try:
            _tenant, identity, membership = self.canonical_authority.resolve(tenant_id, analyst_id, connection=connection)
        except Exception as exc:
            raise PilotAuthorizationError("analyst_tenant_membership_required") from exc
        if identity.status != "active" or membership.status != "active" or membership.role.lower() != "analyst":
            raise PilotAuthorizationError("analyst_role_required")
        if self.auth_service is not None:
            def fetch(owned_connection):
                return owned_connection.execute(
                    "SELECT id, role, is_active, revocation_status, expires_at, actor_id "
                    "FROM users WHERE actor_id=?",
                    (analyst_id,),
                ).fetchone()
            if connection is None:
                with self.db.session() as owned_connection:
                    row = fetch(owned_connection)
            else:
                row = fetch(connection)
            valid_role = row and str(row["role"]).lower() == "analyst"
            valid_state = row and bool(row["is_active"]) and str(row["revocation_status"] or "active") == "active"
            pending_state = (
                row
                and not bool(row["is_active"])
                and str(row["revocation_status"] or "") == "pending"
                and allow_pending
            )
            if not valid_role or not (valid_state or pending_state):
                raise PilotAuthorizationError("active_analyst_account_required")
            if row["expires_at"]:
                try:
                    if datetime.fromisoformat(str(row["expires_at"])) <= self.clock().astimezone(timezone.utc):
                        raise PilotAuthorizationError("active_analyst_account_required")
                except ValueError as exc:
                    raise PilotAuthorizationError("active_analyst_account_required") from exc

    def _validate_manager(self, actor_id: str, tenant_id: str, field: str, *, connection: Any | None = None) -> None:
        if self.canonical_authority is None:
            raise PilotAuthorizationError("canonical_authority_required")
        try:
            _tenant, identity, membership = self.canonical_authority.resolve(
                tenant_id, actor_id, connection=connection
            )
        except Exception as exc:
            raise PilotAuthorizationError(f"{field}_tenant_membership_required") from exc
        if (
            identity.status != "active"
            or membership.status != "active"
            or str(membership.role).lower() not in {"admin", "soc_manager"}
        ):
            raise PilotAuthorizationError(f"{field}_manager_role_required")
        if self.auth_service is not None:
            def fetch(owned_connection):
                return owned_connection.execute(
                    "SELECT role, is_active FROM users WHERE actor_id=?",
                    (actor_id,),
                ).fetchone()
            if connection is None:
                with self.db.session() as owned_connection:
                    row = fetch(owned_connection)
            else:
                row = fetch(connection)
            if not row or not row["is_active"] or str(row["role"]).lower() not in {
                "admin",
                "soc_manager",
            }:
                raise PilotAuthorizationError(f"{field}_active_manager_account_required")

    @staticmethod
    def _normalize_scenarios(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple)) or not values:
            raise PilotAuthorizationError("approved_scenarios_required")
        normalized = tuple(sorted({str(value or "").strip() for value in values}))
        if not normalized or any(not value for value in normalized):
            raise PilotAuthorizationError("approved_scenarios_invalid")
        unknown = sorted(set(normalized) - APPROVED_SCENARIOS)
        if unknown:
            raise PilotAuthorizationError("unsupported_scenario:" + ",".join(unknown))
        if len(normalized) > 10:
            raise PilotAuthorizationError("approved_scenarios_too_many")
        return normalized

    def _invalidate_sessions(self, analyst_id: str, *, connection: Any) -> None:
        if self.auth_service is None:
            return
        row = connection.execute(
            "SELECT id FROM users WHERE actor_id=?", (analyst_id,)
        ).fetchone()
        if row:
            self.auth_service.invalidate_user_sessions(row["id"], connection=connection)

    def _audit(
        self,
        event_type: str,
        authorization: PilotAuthorization,
        *,
        connection: Any,
        actor_id: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if self.audit_service is None:
            return
        payload = {
            "authorization_id": authorization.authorization_id,
            "analyst_id": authorization.analyst_id,
            "tenant_id": authorization.tenant_id,
            "authorization_status": authorization.authorization_status,
            "role": authorization.role,
        }
        payload.update(details or {})
        self.audit_service.record(
            event_type,
            tenant_id=authorization.tenant_id,
            actor_id=actor_id,
            correlation_id=authorization.audit_correlation_id,
            resource_type="pilot_authorization",
            resource_id=authorization.authorization_id,
            operation="write",
            outcome="success",
            details=payload,
            connection=connection,
        )

    @staticmethod
    def _from_row(row: Any) -> PilotAuthorization:
        status = str(row["authorization_status"])
        expires_at = str(row["expires_at"])
        if status == "active" and expires_at <= _utcnow().astimezone(timezone.utc).isoformat():
            status = "expired"
        return PilotAuthorization(
            authorization_id=str(row["authorization_id"]),
            analyst_id=str(row["analyst_id"]),
            tenant_id=str(row["tenant_id"]),
            role=str(row["role"]),
            authorization_status=status,
            authorized_by=str(row["authorized_by"]),
            authorized_at=str(row["authorized_at"]),
            expires_at=expires_at,
            approved_scenarios=tuple(json.loads(row["approved_scenarios_json"])),
            revocation_status=str(row["revocation_status"] or "not_revoked"),
            revoked_at=row["revoked_at"],
            revocation_reason=row["revocation_reason"],
            audit_correlation_id=str(row["audit_correlation_id"] or ""),
        )


__all__ = [
    "APPROVED_SCENARIOS",
    "PilotAuthorization",
    "PilotAuthorizationError",
    "PilotAuthorizationService",
]
