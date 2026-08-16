from .governance_signal import stable_governance_signal_id
from .strategic_decision_lifecycle import StrategicDecisionLifecycle
class StrategicDecisionLifecycleService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("profile","readiness","summary","health") if isinstance(v.get(k),dict)),v) for v in vals]
        v=StrategicDecisionLifecycle(t,stable_governance_signal_id(t,"strategic-decision-lifecycle"),p[0].get("decision_preparation_posture",p[0].get("posture","insufficient_history")),p[0].get("evidence_readiness","insufficient_evidence"),p[0].get("intelligence_availability","insufficient_history"),p[0].get("review_readiness","insufficient_history"),p[0].get("decision_lifecycle_maturity","insufficient_history"),tuple(x for q in p for x in (q.get("recommended_review_areas",()) or ())),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"lifecycle":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["lifecycle"]; return v if v["lifecycle_id"]==i else None
