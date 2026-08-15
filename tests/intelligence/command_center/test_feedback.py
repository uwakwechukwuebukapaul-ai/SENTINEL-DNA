from types import SimpleNamespace
from services.intelligence.command_center.feedback_service import InvestigationFeedbackService

def workspace():
    return SimpleNamespace(tenant_id="a", investigation={"investigation_id":"i1"}, evidence=[{"evidence_id":"e1","status":"available"}], decision={}, events=[], uncertainty="", requires_human_review=True, provenance={"source":"workspace"})
class W:
    def build(self, tenant, investigation): return workspace() if tenant=="a" and investigation=="i1" else None
class O:
    def derive(self, ws): return SimpleNamespace(outcome_id="o1")
def test_feedback_and_quality_are_deterministic_and_advisory():
    service=InvestigationFeedbackService(W(),O()); payload={"outcome_agreement":"disagree","evidence_sufficiency":"partially_sufficient","recommendation_usefulness":"useful","confidence":.8,"reason_codes":["conflict"]}
    first=service.submit("a","i1",payload); result=service.get("a","i1"); assert first.tenant_id=="a" and result["quality"]["status"]=="needs_review" and result["advisory_only"]
    assert service.get("a","i1")["feedback"][0]["outcome_reference"]=="o1"
def test_missing_feedback_is_explicit_and_cross_tenant_isolated():
    service=InvestigationFeedbackService(W(),O()); assert service.get("a","i1")["quality"]["status"]=="insufficient_data"; assert service.get("b","i1") is None
def test_invalid_feedback_does_not_mutate_context():
    service=InvestigationFeedbackService(W(),O())
    try: service.submit("a","i1",{"outcome_agreement":"invalid"}); assert False
    except ValueError: pass
    assert service.get("a","i1")["feedback"]==[]
