from pathlib import Path
from dataclasses import replace
import pytest
from database.connection import DatabaseConnection
from services.identity.binding_administration import IdentityBindingAdministrationService
from services.identity.bindings import IdentityBindingError
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService
from services.tenant.authorization import CanonicalTenantAuthorizationService


def setup(tmp_path):
    db = DatabaseConnection(Path(tmp_path) / "admin.db"); authority = CanonicalAuthorityService(db)
    authority.tenants.create("Acme", "tenant-a"); authority.identities.create("admin@example.com", actor_id="admin"); authority.identities.create("target@example.com", actor_id="target")
    authority.memberships.add("tenant-a", "admin", "admin"); authority.memberships.add("tenant-a", "target", "viewer")
    context = CanonicalRequestContextService(authority).resolve("tenant-a", "admin")
    return IdentityBindingAdministrationService(CanonicalTenantAuthorizationService(authority), db), context


def test_governed_lifecycle(tmp_path):
    service, context = setup(tmp_path); binding = service.create_binding(context, "entra", "subject", "target", "admin")
    assert service.disable_binding(context, binding.binding_id).status == "disabled"
    assert service.reactivate_binding(context, binding.binding_id).status == "active"
    assert service.revoke_binding(context, binding.binding_id).status == "revoked"
    with pytest.raises(IdentityBindingError): service.reactivate_binding(context, binding.binding_id)


def test_non_admin_cannot_create_binding(tmp_path):
    service, context = setup(tmp_path)
    viewer_context = replace(context, actor_id="target", role="viewer")
    with pytest.raises(PermissionError): service.create_binding(viewer_context, "entra", "subject", "target", "target")


def test_target_must_have_active_membership_in_admin_scope(tmp_path):
    service, context = setup(tmp_path)
    with pytest.raises(PermissionError): service.create_binding(context, "entra", "subject", "missing", "admin")
