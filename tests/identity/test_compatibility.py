import pytest
from services.identity.compatibility import DecisionVisibilityResolver, IdentityCompatibility, IdentityResolutionError
from services.identity.models import User
from services.identity.repository import IdentityRepository
from services.tenant.authorization import TenantAuthorizationService

class Decision:
    def __init__(self, tenant_id, eligible_for_feedback=True): self.tenant_id, self.eligible_for_feedback = tenant_id, eligible_for_feedback

class Source:
    def __init__(self): self.items = {("tenant-1", "d1"): Decision("tenant-1")}
    def get(self, tenant_id, decision_id): return self.items.get((tenant_id, decision_id))

def test_identity_resolution_requires_explicit_mapping_and_returns_context():
    repository = IdentityRepository(); repository.save_user(User("user-1", "tenant-1", "analyst", "a@example.com"))
    seam = IdentityCompatibility(organization_to_tenant=lambda org: "tenant-1", legacy_actor_to_canonical=lambda actor, tenant: "user-1", authorization=TenantAuthorizationService(), identity_repository=repository)
    context = seam.resolve(7, "org-1", request_id="req-1", scope=("investigations.read",), role="analyst")
    assert context.tenant_id == "tenant-1" and context.actor_id == "user-1" and context.organization_id == "org-1" and context.role == "analyst"

def test_identity_resolution_fails_closed_for_absent_ambiguous_or_equal_mapping():
    for mapping, error in ((lambda org: None, "mapping_absent"), (lambda org: ["t1", "t2"], "mapping_ambiguous"), (lambda org: org, "mapping_invalid")):
        repository = IdentityRepository(); repository.save_user(User("u", "tenant-1", "u", "u@example.com"))
        seam = IdentityCompatibility(organization_to_tenant=mapping, legacy_actor_to_canonical=lambda actor, tenant: "u", authorization=TenantAuthorizationService(), identity_repository=repository)
        with pytest.raises(IdentityResolutionError, match=error): seam.resolve(1, "org-1", scope=("investigations.read",), role="viewer")

def test_decision_visibility_is_tenant_scoped_and_read_only():
    repository = IdentityRepository(); repository.save_user(User("user-1", "tenant-1", "analyst", "a@example.com"))
    authorization = TenantAuthorizationService()
    seam = IdentityCompatibility(organization_to_tenant=lambda org: "tenant-1", legacy_actor_to_canonical=lambda actor, tenant: "user-1", authorization=authorization, identity_repository=repository)
    context = seam.resolve(1, "org-1", scope=("investigations.read",), role="analyst")
    resolver = DecisionVisibilityResolver(Source(), authorization)
    result = resolver.resolve(context, "d1")
    assert result.exists and result.visible and result.eligible_for_feedback
    assert resolver.resolve(context, "missing").exists is False

def test_decision_visibility_rejects_missing_identifier():
    resolver = DecisionVisibilityResolver(Source(), TenantAuthorizationService())
    context = type("Context", (), {"tenant_id": "tenant-1"})()
    with pytest.raises(IdentityResolutionError, match="decision_id_required"): resolver.resolve(context, "")
