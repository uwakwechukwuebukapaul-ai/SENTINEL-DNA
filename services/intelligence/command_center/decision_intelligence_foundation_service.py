from .governance_signal import stable_governance_signal_id
from .decision_intelligence_foundation import DecisionIntelligenceFoundation
class DecisionIntelligenceFoundationService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("lifecycle","profile","health","summary") if isinstance(v.get(k),dict)),v) for v in vals]
        v=DecisionIntelligenceFoundation(t,stable_governance_signal_id(t,"decision-intelligence-foundation"),p[0].get("review_readiness",p[0].get("posture","insufficient_history")),p[0].get("evidence_readiness","insufficient_evidence"),p[0].get("decision_context_completeness","insufficient_history"),p[0].get("decision_lifecycle_visibility","insufficient_history"),tuple(x for q in p for x in (q.get("strategic_decision_support_signals",()) or ())),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"foundation":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["foundation"]; return v if v["foundation_id"]==i else None
