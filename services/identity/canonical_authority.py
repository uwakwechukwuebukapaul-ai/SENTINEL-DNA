"""Service interfaces for the durable canonical authority.

This module deliberately resolves only canonical IDs. It does not translate
organization IDs or legacy authentication IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    def __init__(self, db: DatabaseConnection = database, auth=None):
        self.db = db
        self.auth = auth

    def create(self, name: str, tenant_id: str | None = None, connection=None) -> CanonicalTenant:
        if not str(name).strip(): raise CanonicalAuthorityError("tenant_name_required")
        if connection is not None:
            return _tenant(CanonicalTenantRepository(connection).create(name, tenant_id))  # type: ignore[arg-type]
        with CanonicalUnitOfWork(self.db) as unit:
            return _tenant(CanonicalTenantRepository(unit.conn).create(name, tenant_id))  # type: ignore[arg-type]

    def get(self, tenant_id: str, connection=None) -> CanonicalTenant | None:
        if connection is not None:
            return _tenant(CanonicalTenantRepository(connection).get(tenant_id))
        with CanonicalUnitOfWork(self.db) as unit: return _tenant(CanonicalTenantRepository(unit.conn).get(tenant_id))

    def set_status(self, tenant_id: str, status: str, connection=None) -> CanonicalTenant | None:
        if status not in {"active", "inactive", "deleted"}: raise CanonicalAuthorityError("invalid_tenant_status")
        if connection is not None:
            repository = CanonicalTenantRepository(connection)
            previous = repository.get(tenant_id)
            result = _tenant(repository.set_status(tenant_id, status))
            if self.auth and previous and previous["status"] != status:
                self.auth.invalidate_tenant_sessions(tenant_id, connection=connection)
            return result
        with CanonicalUnitOfWork(self.db) as unit:
            repository = CanonicalTenantRepository(unit.conn)
            previous = repository.get(tenant_id)
            result = _tenant(repository.set_status(tenant_id, status))
            if self.auth and previous and previous["status"] != status:
                self.auth.invalidate_tenant_sessions(tenant_id, connection=unit.conn)
            return result


class CanonicalIdentityService:
    def __init__(self, db: DatabaseConnection = database): self.db = db

    def create(self, email: str, display_name: str = "", actor_id: str | None = None, connection=None) -> CanonicalIdentity:
        if "@" not in str(email): raise CanonicalAuthorityError("identity_email_required")
        if connection is not None:
            return _identity(CanonicalIdentityRepository(connection).create(email, display_name, actor_id))  # type: ignore[arg-type]
        with CanonicalUnitOfWork(self.db) as unit:
            return _identity(CanonicalIdentityRepository(unit.conn).create(email, display_name, actor_id))  # type: ignore[arg-type]

    def get(self, actor_id: str, connection=None) -> CanonicalIdentity | None:
        if connection is not None:
            return _identity(CanonicalIdentityRepository(connection).get(actor_id))
        with CanonicalUnitOfWork(self.db) as unit: return _identity(CanonicalIdentityRepository(unit.conn).get(actor_id))

    def get_by_email(self, email: str, connection=None) -> CanonicalIdentity | None:
        value = str(email or "").strip().lower()
        if not value:
            return None
        if connection is not None:
            return _identity(connection.execute("SELECT * FROM canonical_identities WHERE email=?", (value,)).fetchone())
        with CanonicalUnitOfWork(self.db) as unit:
            row = unit.conn.execute("SELECT * FROM canonical_identities WHERE email=?", (value,)).fetchone()
            return _identity(row)

    def set_status(self, actor_id: str, status: str, connection=None) -> CanonicalIdentity | None:
        if status not in {"active", "inactive", "deleted"}:
            raise CanonicalAuthorityError("invalid_identity_status")
        now = datetime.now(timezone.utc).isoformat()
        if connection is not None:
            connection.execute("UPDATE canonical_identities SET status=?, updated_at=? WHERE actor_id=?", (status, now, actor_id))
            return _identity(CanonicalIdentityRepository(connection).get(actor_id))
        with CanonicalUnitOfWork(self.db) as unit:
            unit.conn.execute("UPDATE canonical_identities SET status=?, updated_at=? WHERE actor_id=?", (status, now, actor_id))
            return _identity(CanonicalIdentityRepository(unit.conn).get(actor_id))


class CanonicalMembershipService:
    def __init__(self, db: DatabaseConnection = database): self.db = db

    def add(self, tenant_id: str, actor_id: str, role: str = "viewer", connection=None) -> CanonicalMembership:
        if not str(role).strip(): raise CanonicalAuthorityError("membership_role_required")
        if connection is not None:
            return _membership(CanonicalMembershipRepository(connection).add(tenant_id, actor_id, role))
        with CanonicalUnitOfWork(self.db) as unit:
            row = CanonicalMembershipRepository(unit.conn).add(tenant_id, actor_id, role)
            return _membership(row)  # type: ignore[arg-type]

    def get(self, tenant_id: str, actor_id: str, connection=None) -> CanonicalMembership | None:
        if connection is not None:
            return _membership(CanonicalMembershipRepository(connection).get(tenant_id, actor_id))
        with CanonicalUnitOfWork(self.db) as unit: return _membership(CanonicalMembershipRepository(unit.conn).get(tenant_id, actor_id))

    def set_status(self, tenant_id: str, actor_id: str, status: str, connection=None) -> CanonicalMembership | None:
        if status not in {"active", "inactive"}:
            raise CanonicalAuthorityError("invalid_membership_status")
        now = datetime.now(timezone.utc).isoformat()
        if connection is not None:
            connection.execute("UPDATE canonical_memberships SET status=?, updated_at=? WHERE tenant_id=? AND actor_id=?", (status, now, tenant_id, actor_id))
            return _membership(CanonicalMembershipRepository(connection).get(tenant_id, actor_id))
        with CanonicalUnitOfWork(self.db) as unit:
            unit.conn.execute("UPDATE canonical_memberships SET status=?, updated_at=? WHERE tenant_id=? AND actor_id=?", (status, now, tenant_id, actor_id))
            return _membership(CanonicalMembershipRepository(unit.conn).get(tenant_id, actor_id))

    def list_for_actor(self, actor_id: str, connection=None) -> list[CanonicalMembership]:
        if connection is not None:
            return [_membership(row) for row in CanonicalMembershipRepository(connection).list_for_actor(str(actor_id)) if row]
        with CanonicalUnitOfWork(self.db) as unit:
            return [_membership(row) for row in CanonicalMembershipRepository(unit.conn).list_for_actor(str(actor_id)) if row]

    def list_for_tenant(self, tenant_id: str, connection=None) -> list[CanonicalMembership]:
        if connection is not None:
            return [_membership(row) for row in CanonicalMembershipRepository(connection).list_for_tenant(str(tenant_id)) if row]
        with CanonicalUnitOfWork(self.db) as unit:
            return [_membership(row) for row in CanonicalMembershipRepository(unit.conn).list_for_tenant(str(tenant_id)) if row]


class CanonicalAuthorityService:
    """Read/resolve facade used by future canonical context composition."""

    def __init__(self, db: DatabaseConnection = database, auth=None):
        self.db = db
        self.tenants = CanonicalTenantService(db, auth=auth)
        self.identities = CanonicalIdentityService(db)
        self.memberships = CanonicalMembershipService(db)

    def resolve(self, tenant_id: str, actor_id: str, connection=None) -> tuple[CanonicalTenant, CanonicalIdentity, CanonicalMembership]:
        if connection is not None:
            tenants = CanonicalTenantRepository(connection)
            identities = CanonicalIdentityRepository(connection)
            memberships = CanonicalMembershipRepository(connection)
            tenant, identity, membership = _tenant(tenants.get(tenant_id)), _identity(identities.get(actor_id)), _membership(memberships.get(tenant_id, actor_id))
        else:
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
