import pytest

from services.domain_contracts import Feedback, FeedbackOutcome, LearningSignal, learning_signal_from_feedback, learning_signal_from_outcome
from services.intelligence.investigation_optimizer import InvestigationOptimizationService
from services.intelligence.outcome_learning import OutcomeRecord


def test_outcome_adapter_produces_advisory_learning_signal():
    record = OutcomeRecord("tenant-a", "life-1", outcome_id="out-1", verification_status="SUCCESS", confidence=0.8)
    signal = learning_signal_from_outcome(record)
    assert signal.signal_type == "investigation_outcome"
    assert signal.source_id == "out-1"
    assert signal.advisory_only is True


def test_optimizer_consumes_learning_signal_read_only():
    service = InvestigationOptimizationService(tenant_id="tenant-a")
    signal = LearningSignal("s1", "tenant-a", "plan_hint", "out-1", {"steps": ["assess_risk", "collect_evidence"]})
    recommendations = service.recommend_from_learning_signal(signal)
    assert [item.step for item in recommendations] == ["collect_evidence", "assess_risk"]
    assert service.repository.list("tenant-a") == []


def test_optimizer_rejects_malformed_signal_safely():
    service = InvestigationOptimizationService(tenant_id="tenant-a")
    with pytest.raises(ValueError, match="learning_signal_steps_invalid"):
        service.recommend_from_learning_signal(LearningSignal("s1", "tenant-a", "plan_hint", "out-1", {"steps": "bad"}))
    with pytest.raises(TypeError, match="learning_signal_required"):
        service.recommend_from_learning_signal({"steps": []})


def test_optimizer_rejects_cross_tenant_learning_signal():
    service = InvestigationOptimizationService(tenant_id="tenant-a")
    signal = LearningSignal("s1", "tenant-b", "plan_hint", "out-1", {"steps": []})
    with pytest.raises(ValueError, match="learning_signal_tenant_mismatch"):
        service.recommend_from_learning_signal(signal)


def test_optimizer_rejects_unscoped_learning_signal_consumer():
    service = InvestigationOptimizationService()
    signal = LearningSignal("s1", "tenant-a", "plan_hint", "out-1", {"steps": []})
    with pytest.raises(ValueError, match="learning_signal_tenant_scope_required"):
        service.recommend_from_learning_signal(signal)


def test_optimizer_rejects_non_advisory_learning_signal():
    service = InvestigationOptimizationService(tenant_id="tenant-a")
    signal = LearningSignal("s1", "tenant-a", "plan_hint", "out-1", {"steps": []}, advisory_only=False)
    with pytest.raises(ValueError, match="learning_signal_not_advisory"):
        service.recommend_from_learning_signal(signal)


def test_feedback_adapter_produces_advisory_signal_without_mutation():
    feedback = Feedback(
        "fb-1", "tenant-a", "analyst-1", "decision-1", FeedbackOutcome.CORRECTED,
        correction="collect more evidence", confidence=.7,
        outcome_id="out-1", provenance={"source": "decision_feedback"},
    )
    signal = learning_signal_from_feedback(feedback)
    assert signal.signal_type == "decision_feedback"
    assert signal.source_id == "fb-1"
    assert signal.tenant_id == "tenant-a"
    assert signal.value["decision_id"] == "decision-1"
    assert signal.value["user_id"] == "analyst-1"
    assert signal.advisory_only is True
    assert feedback.to_dict()["provenance"] == {"source": "decision_feedback"}


def test_feedback_adapter_rejects_noncanonical_input():
    with pytest.raises(TypeError, match="feedback_required"):
        learning_signal_from_feedback({})
