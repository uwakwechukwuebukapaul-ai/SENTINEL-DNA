from .governance_signal import stable_governance_signal_id
from .executive_intelligence_operating_system import ExecutiveIntelligenceOperatingSystem
class ExecutiveIntelligenceOperatingSystemService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("platform","operating_model","summary","health") if isinstance(v.get(k),dict)),v) for v in vals]
        v=ExecutiveIntelligenceOperatingSystem(t,stable_governance_signal_id(t,"executive-intelligence-operating-system"),p[0].get("governance_platform_posture",p[0].get("intelligence_operating_posture","insufficient_history")),"available" if any(p) else "insufficient_history",tuple(x for q in p for x in (q.get("capability_registry",()) or ())),p[0].get("governance_readiness","insufficient_evidence"),p[0].get("intelligence_lifecycle_visibility","insufficient_history"),p[0].get("evidence_strength","insufficient_evidence"),p[0].get("confidence"),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"operating_system":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["operating_system"]; return v if v["operating_system_id"]==i else None
