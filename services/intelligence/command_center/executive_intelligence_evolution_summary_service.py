from .governance_signal import stable_governance_signal_id
from .executive_intelligence_evolution_summary import ExecutiveIntelligenceEvolutionSummary
class ExecutiveIntelligenceEvolutionSummaryService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("platform","lifecycle","evolution","feedback") if isinstance(v.get(k),dict)),v) for v in vals]; a,b,c,d=p
        v=ExecutiveIntelligenceEvolutionSummary(t,stable_governance_signal_id(t,"executive-intelligence-evolution-summary"),a.get("governance_platform_posture",c.get("intelligence_progression","insufficient_history")),b.get("review_readiness",b.get("evidence_readiness","insufficient_history")),tuple(c.get("capability_evolution_signals",()) or ())+tuple(d.get("improvement_opportunities",()) or ()),tuple(a.get("governance_evolution_signals",()) or ())+tuple(d.get("governance_learning_inputs",()) or ()),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"summary":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["summary"]; return v if v["summary_id"]==i else None
