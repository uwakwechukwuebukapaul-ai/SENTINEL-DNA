import pytest
from services.intelligence.copilot import CopilotProvider, SecurityCopilotService
def workspace(tenant="a",evidence=None): return {"tenant_id":tenant,"case_id":"c1","evidence":evidence if evidence is not None else [{"id":"e1","source":"evidence-engine"}],"investigation":{"confidence":.8},"fabric":{"provenance":[{"source_subsystem":"fabric","source_record_id":"r1"}]}}
def test_evidence_grounded_answer_and_provenance():
    response=SecurityCopilotService("a").answer_question("What supports this?",workspace()); assert "e1" in response.evidence_refs and response.requires_human_review and response.advisory and response.provenance
def test_no_evidence_unknown_and_tenant_isolation():
    service=SecurityCopilotService("a"); response=service.summarize_investigation(workspace("a",[])); assert "Unknown" in response.answer and response.confidence==0
    with pytest.raises(PermissionError): service.answer_question("Explain",workspace("b"))
def test_provider_boundary_and_tts_optional():
    class Provider(CopilotProvider):
        def generate(self,question,context): return {"answer":"provider answer","confidence":None,"uncertainty":"unknown","evidence_refs":[],"reasoning":"provider","recommended_review":"human"}
    service=SecurityCopilotService("a",provider=Provider()); response=service.answer_question("Explain",workspace()); assert response.answer=="provider answer" and service.prepare_review_context(workspace())["tts_enabled"] is False
