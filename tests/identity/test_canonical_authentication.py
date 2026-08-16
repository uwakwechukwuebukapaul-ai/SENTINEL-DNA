from pathlib import Path

import pytest

from database.connection import DatabaseConnection
from services.identity.authentication import (
    CanonicalAuthenticationBoundary,
    CanonicalAuthenticationError,
    CanonicalAuthenticationPrincipal,
)
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService


def boundary(tmp_path):
    authority = CanonicalAuthorityService(DatabaseConnection(Path(tmp_path) / "authentication.db"))
    authority.tenants.create("Acme", "tenant-a")
    authority.identities.create("a@example.com", actor_id="actor-a")
    authority.memberships.add("tenant-a", "actor-a", "admin")
    return CanonicalAuthenticationBoundary(CanonicalRequestContextService(authority)), authority


def test_valid_principal_produces_canonical_request_context(tmp_path):
    service, _ = boundary(tmp_path)
    principal = CanonicalAuthenticationPrincipal("tenant-a", "actor-a", "future_token", "credential-1")
    context = service.compose(principal)
    assert context.tenant_id == "tenant-a"
    assert context.actor_id == "actor-a"
    assert context.role == "admin"


@pytest.mark.parametrize("principal", [None, {"tenant_id": "tenant-a", "actor_id": "actor-a"}])
def test_invalid_principal_fails_closed(tmp_path, principal):
    service, _ = boundary(tmp_path)
    with pytest.raises(CanonicalAuthenticationError, match="canonical_principal_invalid"):
        service.compose(principal)


@pytest.mark.parametrize("tenant_id,actor_id", [("", "actor-a"), ("tenant-a", ""), ("unknown", "actor-a"), ("tenant-a", "unknown")])
def test_invalid_canonical_subject_fails_closed(tmp_path, tenant_id, actor_id):
    service, _ = boundary(tmp_path)
    principal = CanonicalAuthenticationPrincipal(tenant_id, actor_id, "future_token", "credential-1")
    with pytest.raises(CanonicalAuthenticationError): service.compose(principal)


def test_principal_has_no_caller_authority_or_role_fields(tmp_path):
    service, _ = boundary(tmp_path)
    principal = CanonicalAuthenticationPrincipal("tenant-a", "actor-a", "future_token", "credential-1")
    assert not hasattr(principal, "role")
    assert not hasattr(principal, "authority")
    assert service.compose(principal).role == "admin"


def test_inactive_authority_does_not_fall_back_to_legacy_identity(tmp_path):
    service, authority = boundary(tmp_path)
    authority.tenants.set_status("tenant-a", "inactive")
    principal = CanonicalAuthenticationPrincipal("tenant-a", "actor-a", "future_token", "credential-1")
    with pytest.raises(CanonicalAuthenticationError, match="canonical_authentication_denied"):
        service.compose(principal)


def test_each_composition_is_request_scoped(tmp_path):
    service, _ = boundary(tmp_path)
    principal = CanonicalAuthenticationPrincipal("tenant-a", "actor-a", "future_token", "credential-1")
    first, second = service.compose(principal), service.compose(principal)
    assert first is not second
    assert first.request_id != second.request_id

