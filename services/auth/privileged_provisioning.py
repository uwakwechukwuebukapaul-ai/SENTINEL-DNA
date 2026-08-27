"""Guarded operator provisioning for tenant-bound privileged identities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from database.canonical_authority import CanonicalUnitOfWork
from database.connection import DatabaseConnection, database
from database.portability import integrity_error
from services.audit.service import AuditService
from services.identity.canonical_authority import CanonicalAuthorityService

from .auth_service import AuthService


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
TENANT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PRIVILEGED_ROLES = frozenset({"admin", "soc_manager"})
OPERATOR_ACTOR_ID = "operator:privileged-bootstrap"


class PrivilegedProvisioningError(RuntimeError):
    """Safe operator-facing failure without credentials or internal details."""


@dataclass(frozen=True)
class ProvisionedPrivilegedIdentity:
    username: str
    email: str
    tenant_id: str
    role: str
    user_id: int
    actor_id: str


def _validate_username(username: str) -> str:
    value = str(username or "").strip()
    if not USERNAME_PATTERN.fullmatch(value):
        raise PrivilegedProvisioningError("invalid_username")
    if value.lower().startswith("gate1-synthetic-"):
        raise PrivilegedProvisioningError("reserved_identity")
    return value


def _validate_tenant(tenant_id: str) -> str:
    value = str(tenant_id or "").strip()
    if not TENANT_PATTERN.fullmatch(value):
        raise PrivilegedProvisioningError("invalid_tenant")
    return value


def _validate_email(email: str) -> str:
    value = str(email or "").strip().lower()
    if len(value) > 254 or not EMAIL_PATTERN.fullmatch(value):
        raise PrivilegedProvisioningError("invalid_email")
    return value


def _validate_role(role: str) -> str:
    value = str(role or "").strip().lower()
    if value not in PRIVILEGED_ROLES:
        raise PrivilegedProvisioningError("invalid_privileged_role")
    return value


def _validate_password(password: str) -> str:
    value = str(password or "")
    if not value.strip() or len(value) < 10:
        raise PrivilegedProvisioningError("invalid_password")
    return value


class PrivilegedIdentityProvisioningService:
    """Create one tenant-bound privileged identity in one audited transaction."""

    def __init__(
        self,
        auth: AuthService,
        authority: CanonicalAuthorityService,
        audit: AuditService,
        db: DatabaseConnection = database,
    ) -> None:
        self.auth = auth
        self.authority = authority
        self.audit = audit
        self.db = db

    def provision(
        self,
        *,
        username: str,
        email: str,
        tenant_id: str,
        role: str,
        password: str,
        password_confirmation: str,
    ) -> ProvisionedPrivilegedIdentity:
        normalized_username = _validate_username(username)
        normalized_email = _validate_email(email)
        normalized_tenant = _validate_tenant(tenant_id)
        normalized_role = _validate_role(role)
        normalized_password = _validate_password(password)
        if normalized_password != str(password_confirmation or ""):
            raise PrivilegedProvisioningError("password_confirmation_mismatch")

        now = datetime.now(timezone.utc).isoformat()
        actor_id = str(uuid4())

        try:
            with CanonicalUnitOfWork(self.db) as unit:
                tenant = self.authority.tenants.get(normalized_tenant, connection=unit.conn)
                if tenant is None or tenant.status != "active":
                    raise PrivilegedProvisioningError("invalid_tenant")

                if self.auth.get_by_username(normalized_username, connection=unit.conn, include_inactive=True):
                    raise PrivilegedProvisioningError("identity_already_exists")
                if self.auth.get_by_email(normalized_email, connection=unit.conn, include_inactive=True):
                    raise PrivilegedProvisioningError("identity_already_exists")
                if self.authority.identities.get_by_email(normalized_email, connection=unit.conn):
                    raise PrivilegedProvisioningError("identity_already_exists")

                identity = self.authority.identities.create(
                    normalized_email,
                    normalized_username,
                    actor_id,
                    connection=unit.conn,
                )
                membership = self.authority.memberships.add(
                    normalized_tenant,
                    identity.actor_id,
                    normalized_role,
                    connection=unit.conn,
                )
                user = self.auth.register(
                    normalized_username,
                    normalized_email,
                    normalized_password,
                    normalized_role,
                    tenant_id=normalized_tenant,
                    actor_id=identity.actor_id,
                    email_verified_at=now,
                    connection=unit.conn,
                )
                self.audit.record(
                    "PRIVILEGED_IDENTITY_PROVISIONED",
                    user_id=user.id,
                    tenant_id=membership.tenant_id,
                    actor_id=OPERATOR_ACTOR_ID,
                    resource_type="user",
                    resource_id=str(user.id),
                    operation="provision",
                    outcome="success",
                    metadata={
                        "bootstrap": "operator_cli",
                        "role": normalized_role,
                        "username": normalized_username,
                        "actor_id": identity.actor_id,
                    },
                    connection=unit.conn,
                )
                return ProvisionedPrivilegedIdentity(
                    normalized_username,
                    normalized_email,
                    normalized_tenant,
                    normalized_role,
                    int(user.id),
                    identity.actor_id,
                )
        except PrivilegedProvisioningError:
            raise
        except Exception as exc:
            if integrity_error(exc):
                raise PrivilegedProvisioningError("identity_already_exists") from exc
            raise PrivilegedProvisioningError("provisioning_failed") from exc


__all__ = [
    "OPERATOR_ACTOR_ID",
    "PRIVILEGED_ROLES",
    "PrivilegedIdentityProvisioningService",
    "PrivilegedProvisioningError",
    "ProvisionedPrivilegedIdentity",
]
