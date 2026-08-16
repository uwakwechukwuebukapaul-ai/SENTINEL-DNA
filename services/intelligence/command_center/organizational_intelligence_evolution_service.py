from .governance_signal import stable_governance_signal_id
from .organizational_intelligence_evolution import OrganizationalIntelligenceEvolution
class OrganizationalIntelligenceEvolutionService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("maturity","evolution","trends","analytics") if isinstance(v.get(k),dict)),v) for v in vals]
        trend=next((q.get("trend") or q.get("evolution_trend") for q in p if q.get("trend") or q.get("evolution_trend")),"insufficient_history")
        v=OrganizationalIntelligenceEvolution(t,stable_governance_signal_id(t,"organizational-intelligence-evolution"),trend,"Observed maturity movement is presented as advisory interpretation; no causal relationship is established." if trend!="insufficient_history" else "Insufficient history; no causal relationship is established.",tuple(x for q in p for x in (q.get("capability_signals",()) or ())),tuple(x for q in p for x in (q.get("governance_evolution_signals",()) or ())),tuple(x for q in p for x in (q.get("missing_intelligence_areas",()) or ())),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"evolution":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["evolution"]; return v if v["evolution_id"]==i else None
