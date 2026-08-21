"""Service interfaces for the durable canonical authority.

This module deliberately resolves only canonical IDs. It does not translate
organization IDs or legacy authentication IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from database.canonical_authority import (
    CanonicalIdentityRepository,
    CanonicalMembershipRepository,
    CanonicalTenantRepository,
    CanonicalUnitOfWork,
)
from database.connection import DatabaseConnection, database


class CanonicalAuthorityError(ValueError):
    pass


@dataclass(frozen=True)
class CanonicalTenant:
    tenant_id: str
    name: str
    status: str


@dataclass(frozen=True)
class CanonicalIdentity:
    actor_id: str
    email: str
    display_name: str
    status: str


@dataclass(frozen=True)
class CanonicalMembership:
    tenant_id: str
    actor_id: str
    role: str
    status: str


def _tenant(row: Any) -> CanonicalTenant | None:
    return CanonicalTenant(row["tenant_id"], row["name"], row["status"]) if row else None


def _identity(row: Any) -> CanonicalIdentity | None:
    return CanonicalIdentity(row["actor_id"], row["email"], row["display_name"], row["status"]) if row else None


def _membership(row: Any) -> CanonicalMembership | None:
    return CanonicalMembership(row["tenant_id"], row["actor_id"], row["role"], row["status"]) if row else None


class CanonicalTenantService:
    def __init__(self, db: DatabaseConnection = database): self.db = db

    def create(self, name: str, tenant_id: str | None = None) -> CanonicalTenant:
        if not str(name).strip(): raise CanonicalAuthorityError("tenant_name_required")
        with CanonicalUnitOfWork(self.db) as unit:
            return _tenant(CanonicalTenantRepository(unit.conn).create(name, tenant_id))  # type: ignore[arg-type]

    def get(self, tenant_id: str) -> CanonicalTenant | None:
        with CanonicalUnitOfWork(self.db) as unit: return _tenant(CanonicalTenantRepository(unit.conn).get(tenant_id))

    def set_status(self, tenant_id: str, status: str) -> CanonicalTenant | None:
        if status not in {"active", "inactive", "deleted"}: raise CanonicalAuthorityError("invalid_tenant_status")
        with CanonicalUnitOfWork(self.db) as unit: return _tenant(CanonicalTenantRepository(unit.conn).set_status(tenant_id, status))


class CanonicalIdentityService:
    def __init__(self, db: DatabaseConnection = database): self.db = db

    def create(self, email: str, display_name: str = "", actor_id: str | None = None) -> CanonicalIdentity:
        if "@" not in str(email): raise CanonicalAuthorityError("identity_email_required")
        with CanonicalUnitOfWork(self.db) as unit:
            return _identity(CanonicalIdentityRepository(unit.conn).create(email, display_name, actor_id))  # type: ignore[arg-type]

    def get(self, actor_id: str) -> CanonicalIdentity | None:
        with CanonicalUnitOfWork(self.db) as unit: return _identity(CanonicalIdentityRepository(unit.conn).get(actor_id))

    def get_by_email(self, email: str) -> CanonicalIdentity | None:
        value = str(email or "").strip().lower()
        if not value:
            return None
        with CanonicalUnitOfWork(self.db) as unit:
            row = unit.conn.execute("SELECT * FROM canonical_identities WHERE email=?", (value,)).fetchone()
            return _identity(row)


class CanonicalMembershipService:
    def __init__(self, db: DatabaseConnection = database): self.db = db

    def add(self, tenant_id: str, actor_id: str, role: str = "viewer") -> CanonicalMembership:
        if not str(role).strip(): raise CanonicalAuthorityError("membership_role_required")
        with CanonicalUnitOfWork(self.db) as unit:
            row = CanonicalMembershipRepository(unit.conn).add(tenant_id, actor_id, role)
            return _membership(row)  # type: ignore[arg-type]

    def get(self, tenant_id: str, actor_id: str) -> CanonicalMembership | None:
        with CanonicalUnitOfWork(self.db) as unit: return _membership(CanonicalMembershipRepository(unit.conn).get(tenant_id, actor_id))

    def list_for_actor(self, actor_id: str) -> list[CanonicalMembership]:
        with CanonicalUnitOfWork(self.db) as unit:
            return [_membership(row) for row in CanonicalMembershipRepository(unit.conn).list_for_actor(str(actor_id)) if row]


class CanonicalAuthorityService:
    """Read/resolve facade used by future canonical context composition."""

    def __init__(self, db: DatabaseConnection = database):
        self.db = db
        self.tenants = CanonicalTenantService(db)
        self.identities = CanonicalIdentityService(db)
        self.memberships = CanonicalMembershipService(db)

    def resolve(self, tenant_id: str, actor_id: str) -> tuple[CanonicalTenant, CanonicalIdentity, CanonicalMembership]:
        with CanonicalUnitOfWork(self.db) as unit:
            tenants = CanonicalTenantRepository(unit.conn)
            identities = CanonicalIdentityRepository(unit.conn)
            memberships = CanonicalMembershipRepository(unit.conn)
            tenant, identity, membership = _tenant(tenants.get(tenant_id)), _identity(identities.get(actor_id)), _membership(memberships.get(tenant_id, actor_id))
        if not tenant: raise CanonicalAuthorityError("canonical_tenant_not_found")
        if not identity: raise CanonicalAuthorityError("canonical_identity_not_found")
        if not membership: raise CanonicalAuthorityError("canonical_membership_not_found")
        if tenant.status != "active": raise CanonicalAuthorityError("canonical_tenant_inactive")
        if identity.status != "active": raise CanonicalAuthorityError("canonical_identity_inactive")
        if membership.status != "active": raise CanonicalAuthorityError("canonical_membership_inactive")
        return tenant, identity, membership
