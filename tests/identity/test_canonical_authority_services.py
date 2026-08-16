import pytest

from database.connection import DatabaseConnection
from services.identity.canonical_authority import CanonicalAuthorityError, CanonicalAuthorityService


def test_services_create_and_resolve_canonical_records(tmp_path):
    service = CanonicalAuthorityService(DatabaseConnection(tmp_path / "authority.db"))
    tenant = service.tenants.create("Acme", "tenant-1")
    identity = service.identities.create("a@example.com", actor_id="actor-1")
    service.memberships.add(tenant.tenant_id, identity.actor_id, "admin")
    resolved = service.resolve(tenant.tenant_id, identity.actor_id)
    assert resolved[2].role == "admin"


def test_resolver_rejects_inactive_canonical_records(tmp_path):
    service = CanonicalAuthorityService(DatabaseConnection(tmp_path / "authority.db"))
    tenant = service.tenants.create("Acme", "tenant-1")
    identity = service.identities.create("a@example.com", actor_id="actor-1")
    service.memberships.add("tenant-1", "actor-1")
    service.tenants.set_status(tenant.tenant_id, "inactive")
    with pytest.raises(CanonicalAuthorityError, match="canonical_tenant_inactive"):
        service.resolve(tenant.tenant_id, identity.actor_id)

