import pytest

from services.domain_contracts import (
    FeedbackOutcome,
    LearningSignal,
    Outcome,
    OutcomeStatus,
    QualityScope,
    feedback_from_store_record,
)
from services.intelligence.outcome_learning import OutcomeRecord


def test_outcome_is_deterministically_serializable():
    value = Outcome("tenant-a", "life-1", "out-1", status=OutcomeStatus.SUCCESS, evidence_references=("e1",))
    assert value.to_dict()["status"] == "SUCCESS"
    assert value.to_dict()["evidence_references"] == ["e1"]


def test_feedback_adapter_normalizes_organization_identity():
    value = feedback_from_store_record({"id": "f1", "organization_id": "tenant-a", "user_id": "u1", "decision_id": "d1", "outcome": "approved"})
    assert value.tenant_id == "tenant-a"
    assert value.outcome is FeedbackOutcome.APPROVED


def test_outcome_adapter_contract_remains_independent_of_implementation_model():
    record = OutcomeRecord("tenant-a", "life-1", outcome_id="out-1", verification_status="SUCCESS")
    from services.domain_contracts.adapters import outcome_from_record
    assert outcome_from_record(record).verification_status is OutcomeStatus.SUCCESS


def test_contracts_reject_missing_identity_and_invalid_confidence():
    with pytest.raises(ValueError, match="tenant_id_required"):
        Outcome("", "life-1", "out-1")
    with pytest.raises(ValueError, match="confidence_out_of_range"):
        LearningSignal("s1", "tenant-a", "pattern", "p1", confidence=2)


def test_learning_signal_is_advisory_and_serializable():
    value = LearningSignal("s1", "tenant-a", "pattern", "p1", confidence=0.5)
    assert value.advisory_only is True
    assert value.to_dict()["confidence"] == 0.5
    assert QualityScope.OUTCOME.value == "outcome"
