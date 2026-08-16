from dataclasses import replace
from pathlib import Path
import pytest

from database.connection import DatabaseConnection
from services.identity.binding_admin_api import BindingAdminAPIError, IdentityBindingAdminAPI
from services.identity.binding_administration import IdentityBindingAdministrationService
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService
from services.tenant.authorization import CanonicalTenantAuthorizationService


def setup(tmp_path):
    db = DatabaseConnection(Path(tmp_path) / "api.db"); authority = CanonicalAuthorityService(db)
    authority.tenants.create("Acme", "tenant-a"); authority.identities.create("admin@example.com", actor_id="admin"); authority.identities.create("target@example.com", actor_id="target")
    authority.memberships.add("tenant-a", "admin", "admin"); authority.memberships.add("tenant-a", "target", "viewer")
    context = CanonicalRequestContextService(authority).resolve("tenant-a", "admin")
    administration = IdentityBindingAdministrationService(CanonicalTenantAuthorizationService(authority), db)
    return IdentityBindingAdminAPI(administration), context


def test_valid_context_only_api_delegates_governed_create(tmp_path):
    api, context = setup(tmp_path)
    binding = api.create(context, {"provider": "entra", "external_subject": "sub", "actor_id": "target", "created_by": "admin"})
    assert binding.actor_id == "target"


@pytest.mark.parametrize("payload", [{"provider": "entra", "external_subject": "sub", "actor_id": "target", "created_by": "admin", "role": "admin"}, None, {"provider": "entra"}])
def test_api_rejects_malformed_or_security_sensitive_payload(tmp_path, payload):
    api, context = setup(tmp_path)
    with pytest.raises(BindingAdminAPIError): api.create(context, payload)


def test_api_never_accepts_tenant_as_authority_or_legacy_session(tmp_path):
    api, context = setup(tmp_path)
    with pytest.raises(BindingAdminAPIError): api.create(context, {"provider": "entra", "external_subject": "sub", "actor_id": "target", "created_by": "admin", "tenant_id": "tenant-a"})


def test_non_admin_canonical_context_is_rejected(tmp_path):
    api, context = setup(tmp_path)
    viewer = replace(context, actor_id="target", role="viewer")
    with pytest.raises(PermissionError): api.create(viewer, {"provider": "entra", "external_subject": "sub", "actor_id": "target", "created_by": "target"})


def test_api_delegates_lifecycle_without_direct_repository_access(tmp_path):
    api, context = setup(tmp_path)
    binding = api.create(context, {"provider": "entra", "external_subject": "sub", "actor_id": "target", "created_by": "admin"})
    assert api.disable(context, binding.binding_id).status == "disabled"
    assert api.reactivate(context, binding.binding_id).status == "active"
    assert api.revoke(context, binding.binding_id).status == "revoked"
