from .governance_signal import stable_governance_signal_id
from .executive_intelligence_governance_platform import ExecutiveIntelligenceGovernancePlatform
class ExecutiveIntelligenceGovernancePlatformService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("operating_model","summary","governance","maturity") if isinstance(v.get(k),dict)),v) for v in vals]
        v=ExecutiveIntelligenceGovernancePlatform(t,stable_governance_signal_id(t,"executive-intelligence-governance-platform"),p[0].get("governance_platform_posture",p[0].get("governance_readiness","insufficient_history")),"visible" if any(p) else "insufficient_history",p[0].get("intelligence_ownership_visibility","insufficient_history"),p[0].get("governance_control_maturity","insufficient_evidence"),p[0].get("review_process_readiness","insufficient_history"),tuple(x for q in p for x in (q.get("governance_evolution_signals",()) or ())),p[0].get("evidence_strength","insufficient_evidence"),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"platform":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["platform"]; return v if v["platform_id"]==i else None
