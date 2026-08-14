from services.intelligence.copilot import SecurityCopilotService
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_context_and_explanation():
    response=SecurityCopilotService("a").explain({"case_id":"c1", "evidence":[{"id":"E1"}]}); assert response.evidence_refs == ["E1"] and response.confidence > 0

def test_tenant_isolation_and_audit():
    history=[]
    class Audit:
        def record(self, event, **payload): history.append(payload)
    service=SecurityCopilotService("a", audit_logger=Audit()); service.ask("summarize", {"case_id":"c1"}); assert len(service.repository.history("a")) == 1 and service.repository.history("b") == [] and history

def test_recommendation_is_non_autonomous():
    assert SecurityCopilotService("a").recommend({}).metadata["autonomous_actions"] is False

def test_backward_compatibility():
    result=InvestigationResult(); assert result.copilot_context is None and "copilot_context" in result.to_dict()
