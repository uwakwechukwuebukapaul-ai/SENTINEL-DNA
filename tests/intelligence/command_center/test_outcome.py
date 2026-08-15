from types import SimpleNamespace
from services.intelligence.command_center.outcome_service import InvestigationOutcomeService

def workspace(**overrides):
    data=dict(tenant_id="a", investigation={"investigation_id":"i1","outcome_category":"confirmed_threat","confidence":.9}, evidence=[{"evidence_id":"e1","status":"available"}], decision={"decision_context_id":"d1","decision_state":"completed_reference","confidence":.9}, events=[{"event_id":"ev1","confidence":.9}], uncertainty="", requires_human_review=False, provenance={"source":"test"})
    data.update(overrides); return SimpleNamespace(**data)

def test_outcome_is_deterministic_and_evidence_grounded():
    service=InvestigationOutcomeService(); a=service.derive(workspace()); b=service.derive(workspace())
    assert a.to_dict()==b.to_dict() and a.outcome_category=="confirmed_threat" and a.supporting_evidence==["e1"] and a.advisory_only

def test_insufficient_evidence_and_unresolved_decision_require_review():
    result=InvestigationOutcomeService().derive(workspace(evidence=[{"evidence_id":"missing","status":"unavailable"}],decision={"decision_context_id":"d1","decision_state":"pending_review"},uncertainty="evidence_unavailable"))
    assert result.outcome_category=="insufficient_evidence" and result.requires_human_review and "decision_pending" in result.unresolved_items

def test_low_confidence_preserved_without_mutating_workspace():
    source=workspace(investigation={"investigation_id":"i1","outcome_category":"confirmed_threat","confidence":.4}); before=source.__dict__.copy(); result=InvestigationOutcomeService().derive(source)
    assert source.__dict__==before and result.confidence==.4 and "low_confidence" in result.uncertainty and result.requires_human_review
