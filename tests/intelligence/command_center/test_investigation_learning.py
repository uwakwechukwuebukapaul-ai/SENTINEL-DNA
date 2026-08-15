from types import SimpleNamespace
from services.intelligence.command_center.learning_service import AnalystInvestigationLearningService
class Q:
    def __init__(self, **kw):
        defaults={"tenant_id":"a","investigation_count":2,"feedback_count":2,"quality_signal_count":2,"agreement_count":0,"disagreement_count":2,"unresolved_count":1,"human_review_count":1,"evidence_insufficient_count":1,"average_confidence":.5,"uncertainty":["conflicting_feedback"],"trend_direction":"needs_review","provenance":{"source":"quality"},"contributing_feedback_ids":["f1","f2"],"contributing_investigation_ids":["i1","i2"]}; defaults.update(kw); self.__dict__.update(defaults)
class S:
    def __init__(self,q): self.q=q
    def derive(self,tenant): return self.q
def test_learning_is_deterministic_and_detects_patterns():
    service=AnalystInvestigationLearningService(S(Q())); first=service.derive("a"); second=service.derive("a")
    assert [x.to_dict() for x in first]==[x.to_dict() for x in second] and first[0].learning_type=="repeated_disagreement" and first[0].contributing_feedback_ids==["f1","f2"]
def test_empty_learning_is_explicit_and_tenant_scoped():
    q=Q(investigation_count=0,feedback_count=0,quality_signal_count=0,disagreement_count=0,unresolved_count=0,human_review_count=0,evidence_insufficient_count=0,uncertainty=[] ,contributing_feedback_ids=[],contributing_investigation_ids=[])
    result=AnalystInvestigationLearningService(S(q)).derive("a"); assert len(result)==1 and result[0].learning_type=="insufficient_data" and result[0].tenant_id=="a"
