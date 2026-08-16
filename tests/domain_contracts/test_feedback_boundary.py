import pytest

from services.domain_contracts import FeedbackReadBoundary
from services.identity.compatibility import CanonicalIdentityContext
from services.intelligence.feedback.store import FeedbackStore
from services.tenant.authorization import TenantAuthorizationService


def context(tenant="tenant-1", actor="user-1", role="analyst"):
    return CanonicalIdentityContext(
        tenant_id=tenant,
        actor_id=actor,
        role=role,
        authorization_scope=("investigations.read",),
    )


def test_boundary_reads_legacy_records_as_canonical_feedback_without_mutation():
    store = FeedbackStore()
    store.record("org-1", "user-1", "decision-1", "approved", confidence=.9)
    before = list(store.records)
    boundary = FeedbackReadBoundary(store, lambda tenant: "org-1", TenantAuthorizationService())

    result = boundary.list(context())

    assert len(result) == 1
    assert result[0].tenant_id == "tenant-1"
    assert result[0].user_id == "user-1"
    assert result[0].decision_id == "decision-1"
    assert store.records == before


def test_boundary_is_tenant_scoped_and_requires_explicit_mapping():
    store = FeedbackStore()
    store.record("org-1", "user-1", "decision-1", "approved")
    store.record("org-2", "user-2", "decision-2", "rejected")
    boundary = FeedbackReadBoundary(store, lambda tenant: {"tenant-1": "org-1"}.get(tenant), TenantAuthorizationService())

    assert [item.decision_id for item in boundary.list(context())] == ["decision-1"]
    with pytest.raises(ValueError, match="mapping_invalid"):
        boundary.list(context("tenant-2", "user-2"))


def test_boundary_uses_real_authorization_and_fails_closed():
    store = FeedbackStore()
    store.record("org-1", "user-1", "decision-1", "approved")
    boundary = FeedbackReadBoundary(store, lambda tenant: "org-1", TenantAuthorizationService())

    with pytest.raises(PermissionError, match="tenant_access_denied"):
        boundary.list(context(role="unknown"))
