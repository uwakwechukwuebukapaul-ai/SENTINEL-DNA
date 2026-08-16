import pytest

from services.domain_contracts import (
    DecisionFeedbackWriteBoundary,
    Feedback,
    FeedbackOutcome,
)
from services.identity.compatibility import CanonicalIdentityContext
from services.intelligence.command_center.decision import DecisionContext
from services.intelligence.command_center.decision_repository import DecisionContextRepository
from services.intelligence.feedback.store import FeedbackStore
from services.tenant.authorization import TenantAuthorizationService


def context(tenant="tenant-1", actor="user-1", role="analyst"):
    return CanonicalIdentityContext(
        tenant_id=tenant,
        actor_id=actor,
        role=role,
        authorization_scope=("investigations.read",),
    )


def feedback(tenant="tenant-1", actor="user-1", decision="decision-1"):
    return Feedback(
        "feedback-1", tenant, actor, decision, FeedbackOutcome.APPROVED,
        correction="confirmed", confidence=.9, provenance={"source": "test"},
    )


class RecordingStore(FeedbackStore):
    def __init__(self):
        super().__init__()
        self.calls = []

    def record(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return super().record(*args, **kwargs)


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))


def boundary(mapping=lambda tenant: "org-1", role="analyst"):
    decisions = DecisionContextRepository()
    decision = DecisionContext("decision-1", "tenant-1")
    decisions.save(decision)
    store = RecordingStore()
    return (
        DecisionFeedbackWriteBoundary(
            decisions, store, mapping, TenantAuthorizationService()
        ),
        store,
        decision,
    )


def test_authorized_submission_preserves_identity_and_uses_legacy_organization():
    boundary_instance, store, decision = boundary()
    result = boundary_instance.submit(context(), feedback())

    assert result.tenant_id == "tenant-1"
    assert result.user_id == "user-1"
    assert result.decision_id == "decision-1"
    assert result.provenance["actor_id"] == "user-1"
    assert store.calls[0][0][:4] == ("org-1", "user-1", "decision-1", "approved")
    assert decision.tenant_id == "tenant-1"


def test_authorized_submission_emits_existing_audit_event_with_provenance():
    decisions = DecisionContextRepository()
    decisions.save(DecisionContext("decision-1", "tenant-1"))
    store = RecordingStore()
    audit = Audit()
    boundary_instance = DecisionFeedbackWriteBoundary(
        decisions, store, lambda tenant: "org-1", TenantAuthorizationService(), audit
    )

    boundary_instance.submit(context(), feedback())

    event, payload = audit.events[0]
    assert event == "DECISION_FEEDBACK_RECORDED"
    assert payload["user_id"] == "user-1"
    assert payload["details"]["tenant_id"] == "tenant-1"
    assert payload["details"]["decision_id"] == "decision-1"


def test_rejected_submissions_emit_no_audit_event():
    decisions = DecisionContextRepository()
    decisions.save(DecisionContext("decision-1", "tenant-1"))
    store = RecordingStore()
    audit = Audit()
    boundary_instance = DecisionFeedbackWriteBoundary(
        decisions, store, lambda tenant: "org-1", TenantAuthorizationService(), audit
    )

    with pytest.raises(ValueError, match="decision_not_found"):
        boundary_instance.submit(context(), feedback(decision="missing"))
    with pytest.raises(PermissionError, match="tenant_access_denied"):
        boundary_instance.submit(context(role="unknown"), feedback())

    assert audit.events == []


@pytest.mark.parametrize(
    "bad_context, error",
    [(context("", "user-1"), "tenant_id_required"),
     (context("tenant-1", ""), "actor_id_required")],
)
def test_missing_canonical_identity_fails_closed(bad_context, error):
    boundary_instance, _, _ = boundary()
    with pytest.raises(ValueError, match=error):
        boundary_instance.submit(bad_context, feedback())


def test_missing_decision_is_rejected():
    boundary_instance, _, _ = boundary()
    with pytest.raises(ValueError, match="decision_id_required"):
        boundary_instance.submit(context(), feedback(decision=""))


def test_nonexistent_and_cross_tenant_decisions_are_rejected():
    boundary_instance, _, _ = boundary()
    with pytest.raises(ValueError, match="decision_not_found"):
        boundary_instance.submit(context(), feedback(decision="missing"))
    with pytest.raises(ValueError, match="feedback_tenant_mismatch"):
        boundary_instance.submit(context(), feedback(tenant="tenant-2"))


def test_invalid_mapping_and_unauthorized_actor_are_rejected():
    boundary_instance, _, _ = boundary(lambda tenant: tenant)
    with pytest.raises(ValueError, match="mapping_invalid"):
        boundary_instance.submit(context(), feedback())

    boundary_instance, _, _ = boundary()
    with pytest.raises(PermissionError, match="tenant_access_denied"):
        boundary_instance.submit(context(role="unknown"), feedback())


def test_existing_feedback_store_repeated_submission_semantics_are_preserved():
    boundary_instance, store, _ = boundary()
    boundary_instance.submit(context(), feedback())
    second = boundary_instance.submit(
        context(), Feedback("feedback-2", "tenant-1", "user-1", "decision-1", FeedbackOutcome.REJECTED)
    )
    assert len(store.list("org-1")) == 2
    assert second.outcome is FeedbackOutcome.REJECTED
