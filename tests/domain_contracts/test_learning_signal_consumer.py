import pytest

from services.domain_contracts import LearningSignal, learning_signal_from_outcome
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
