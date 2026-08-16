from .governance_signal import stable_governance_signal_id
from .intelligence_operating_model import IntelligenceOperatingModel
class IntelligenceOperatingModelService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("maturity","adoption","feedback","platform") if isinstance(v.get(k),dict)),v) for v in vals]
        v=IntelligenceOperatingModel(t,stable_governance_signal_id(t,"intelligence-operating-model"),p[0].get("ai_maturity_level",p[0].get("operating_model_maturity","insufficient_history")),tuple(x for q in p for x in (q.get("intelligence_capability_gaps",q.get("coverage_gaps",())) or ())),tuple(x for q in p for x in (q.get("intelligence_usefulness_signals",()) or ())),tuple(x for q in p for x in (q.get("improvement_opportunities",()) or ())),p[0].get("evidence_strength","insufficient_evidence"),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"operating_model":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["operating_model"]; return v if v["model_id"]==i else None
