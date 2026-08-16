import pytest

from services.domain_contracts import Feedback, FeedbackOutcome, LearningSignal
from services.intelligence.investigation_optimizer import (
    FeedbackRecommendationService,
    InvestigationOptimizationService,
)


def feedback(tenant="tenant-a", provenance=None):
    return Feedback(
        "feedback-1", tenant, "analyst-1", "decision-1", FeedbackOutcome.APPROVED,
        provenance={"source": "decision_feedback"} if provenance is None else provenance,
    )


class RecordingOptimizer:
    def __init__(self):
        self.signal = None
        self.result = object()

    def recommend_from_learning_signal(self, signal):
        self.signal = signal
        return self.result


def test_canonical_feedback_is_adapted_and_result_is_returned_unchanged():
    optimizer = RecordingOptimizer()
    service = FeedbackRecommendationService(optimizer)

    result = service.recommend_from_feedback(feedback())

    assert result is optimizer.result
    assert isinstance(optimizer.signal, LearningSignal)
    assert optimizer.signal.tenant_id == "tenant-a"
    assert optimizer.signal.value["decision_id"] == "decision-1"
    assert optimizer.signal.provenance["source"] == "decision_feedback"


def test_noncanonical_feedback_and_missing_optimizer_fail_closed():
    with pytest.raises(ValueError, match="optimizer_required"):
        FeedbackRecommendationService(None)
    with pytest.raises(TypeError, match="feedback_required"):
        FeedbackRecommendationService(RecordingOptimizer()).recommend_from_feedback({})


def test_real_optimizer_rejects_cross_tenant_feedback():
    service = FeedbackRecommendationService(
        InvestigationOptimizationService(tenant_id="tenant-a")
    )
    with pytest.raises(ValueError, match="learning_signal_tenant_mismatch"):
        service.recommend_from_feedback(feedback(tenant="tenant-b"))


def test_real_optimizer_rejects_missing_feedback_provenance():
    service = FeedbackRecommendationService(
        InvestigationOptimizationService(tenant_id="tenant-a")
    )
    with pytest.raises(ValueError, match="feedback_provenance_required"):
        service.recommend_from_feedback(feedback(provenance={}))
