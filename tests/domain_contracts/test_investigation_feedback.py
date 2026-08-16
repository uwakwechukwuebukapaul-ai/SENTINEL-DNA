import pytest

from services.domain_contracts import InvestigationFeedback, InvestigationFeedbackAdapter
from services.intelligence.command_center.feedback import AnalystInvestigationFeedback
from services.intelligence.command_center.feedback_service import FeedbackRepository


def value(index="1", investigation="inv-1", tenant="tenant-a"):
    return InvestigationFeedback(
        feedback_id=f"fb-{index}", tenant_id=tenant, investigation_id=investigation,
        outcome_reference="out-1", analyst_reference="analyst-1",
        outcome_agreement="partially_agree", evidence_sufficiency="sufficient",
        recommendation_usefulness="useful", confidence=.8,
        reason_codes=("r1",), supporting_references=("e1",),
        provenance={"source": "test"}, created_at="2026-01-01T00:00:00+00:00",
    )


def test_existing_record_maps_losslessly_to_canonical_contract():
    record = AnalystInvestigationFeedback(**value().to_dict())
    canonical = InvestigationFeedbackAdapter.to_contract(record)
    assert canonical.to_dict() == value().to_dict()


def test_canonical_maps_back_without_semantic_substitution():
    record = InvestigationFeedbackAdapter.to_record(value())
    assert record.to_dict() == value().to_dict()


def test_repository_adapter_preserves_tenant_order_and_multiple_submissions():
    adapter = InvestigationFeedbackAdapter(FeedbackRepository())
    first, second = value("1"), value("2")
    adapter.save(first)
    adapter.save(second)
    assert [x.feedback_id for x in adapter.list("tenant-a", "inv-1")] == ["fb-1", "fb-2"]
    assert adapter.list("tenant-b", "inv-1") == []


def test_optional_fields_and_invalid_inputs_are_deterministic():
    minimal = InvestigationFeedback("fb", "tenant", "inv")
    assert InvestigationFeedbackAdapter.to_record(minimal).to_dict()["created_at"] == ""
    with pytest.raises(ValueError, match="tenant_id_required"):
        InvestigationFeedbackAdapter(FeedbackRepository()).list("", "inv")
    with pytest.raises(TypeError, match="investigation_feedback_required"):
        InvestigationFeedbackAdapter.to_record({})
