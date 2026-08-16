from dataclasses import dataclass

import pytest

from database.connection import DatabaseConnection
from services.identity.canonical_authority import CanonicalAuthorityService
from services.tenant.authorization import CanonicalTenantAuthorizationService


@dataclass
class Context:
    tenant_id: str
    actor_id: str
    role: str = "viewer"


def authority(tmp_path):
    service = CanonicalAuthorityService(DatabaseConnection(tmp_path / "authorization.db"))
    service.tenants.create("Acme", "tenant-a")
    service.tenants.create("Other", "tenant-b")
    service.identities.create("a@example.com", actor_id="actor-a")
    service.identities.create("b@example.com", actor_id="actor-b")
    service.memberships.add("tenant-a", "actor-a", "admin")
    service.memberships.add("tenant-b", "actor-b", "viewer")
    return service


def test_valid_and_cross_tenant_resolution_fail_closed(tmp_path):
    auth = CanonicalTenantAuthorizationService(authority(tmp_path))
    assert auth.can_access_resource(Context("tenant-a", "actor-a"), "tenant-a", "cases.write")
    assert not auth.can_access_resource(Context("tenant-a", "actor-a"), "tenant-b", "cases.read")
    assert not auth.can_access_resource(Context("tenant-a", "actor-b"), "tenant-a", "cases.read")


@pytest.mark.parametrize("missing", ["tenant", "actor"])
def test_missing_canonical_context_fails_closed(tmp_path, missing):
    auth = CanonicalTenantAuthorizationService(authority(tmp_path))
    context = Context("" if missing == "tenant" else "tenant-a", "" if missing == "actor" else "actor-a")
    with pytest.raises(PermissionError): auth.require_permission(context, "tenant-a", "cases.read")


@pytest.mark.parametrize("target", ["tenant", "identity", "membership"])
def test_inactive_canonical_authority_is_rejected(tmp_path, target):
    service = authority(tmp_path)
    if target == "tenant": service.tenants.set_status("tenant-a", "inactive")
    elif target == "identity":
        with service.db.session() as conn: conn.execute("UPDATE canonical_identities SET status='inactive' WHERE actor_id='actor-a'")
    else:
        with service.db.session() as conn: conn.execute("UPDATE canonical_memberships SET status='inactive' WHERE tenant_id='tenant-a' AND actor_id='actor-a'")
    auth = CanonicalTenantAuthorizationService(service)
    with pytest.raises(PermissionError): auth.require_permission(Context("tenant-a", "actor-a"), "tenant-a", "cases.read")

