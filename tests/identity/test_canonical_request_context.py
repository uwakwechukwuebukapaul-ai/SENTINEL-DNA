from dataclasses import FrozenInstanceError

import pytest

from database.connection import DatabaseConnection
from services.identity.canonical_authority import CanonicalAuthorityError, CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService


def authority(tmp_path):
    service = CanonicalAuthorityService(DatabaseConnection(tmp_path / "request-context.db"))
    service.tenants.create("Acme", "tenant-a")
    service.identities.create("a@example.com", actor_id="actor-a")
    service.memberships.add("tenant-a", "actor-a", "admin")
    return service


def test_valid_context_uses_membership_role_and_is_immutable(tmp_path):
    context = CanonicalRequestContextService(authority(tmp_path)).resolve("tenant-a", "actor-a")
    assert context.tenant_id == "tenant-a"
    assert context.actor_id == "actor-a"
    assert context.role == "admin"
    with pytest.raises(FrozenInstanceError): context.role = "owner"


@pytest.mark.parametrize(("tenant_id", "actor_id"), [("", "actor-a"), ("tenant-a", "")], ids=["missing-tenant", "missing-actor"])
def test_missing_canonical_identifier_fails_closed(tmp_path, tenant_id, actor_id):
    with pytest.raises(CanonicalAuthorityError):
        CanonicalRequestContextService(authority(tmp_path)).resolve(tenant_id, actor_id)


@pytest.mark.parametrize(("tenant_id", "actor_id"), [("unknown", "actor-a"), ("tenant-a", "unknown"), ("tenant-a", "actor-b")])
def test_invalid_canonical_pair_fails_closed(tmp_path, tenant_id, actor_id):
    with pytest.raises(CanonicalAuthorityError, match="canonical_request_context_denied"):
        CanonicalRequestContextService(authority(tmp_path)).resolve(tenant_id, actor_id)


@pytest.mark.parametrize("target", ["tenant", "identity", "membership"])
def test_inactive_authority_fails_closed(tmp_path, target):
    service = authority(tmp_path)
    if target == "tenant": service.tenants.set_status("tenant-a", "inactive")
    elif target == "identity":
        with service.db.session() as connection: connection.execute("UPDATE canonical_identities SET status='inactive' WHERE actor_id='actor-a'")
    else:
        with service.db.session() as connection: connection.execute("UPDATE canonical_memberships SET status='inactive' WHERE tenant_id='tenant-a' AND actor_id='actor-a'")
    with pytest.raises(CanonicalAuthorityError, match="canonical_request_context_denied"):
        CanonicalRequestContextService(service).resolve("tenant-a", "actor-a")


def test_contexts_are_request_scoped_and_not_reused(tmp_path):
    service = CanonicalRequestContextService(authority(tmp_path))
    first = service.resolve("tenant-a", "actor-a")
    second = service.resolve("tenant-a", "actor-a")
    assert first is not second
    assert first.request_id != second.request_id

