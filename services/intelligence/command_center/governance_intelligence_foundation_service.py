from .governance_signal import stable_governance_signal_id
from .governance_intelligence_foundation import GovernanceIntelligenceFoundation
class GovernanceIntelligenceFoundationService:
    def __init__(self,*sources): self.sources=sources
    def derive(self,t):
        vals=[s.derive(t) if s else {} for s in self.sources]; p=[next((v[k] for k in ("platform","governance","summary","adoption") if isinstance(v.get(k),dict)),v) for v in vals]
        v=GovernanceIntelligenceFoundation(t,stable_governance_signal_id(t,"governance-intelligence-foundation"),"advisory_review_ready" if any(p) else "insufficient_evidence","visible" if any(p) else "insufficient_history",tuple(x for q in p for x in (q.get("governance_alignment_signals",()) or ())), ("human_review_required","no_autonomous_execution"),p[0].get("evidence_strength","insufficient_evidence"),tuple(sorted({u for q in p for u in (q.get("uncertainty",()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get("provenance",()) or ())})),True)
        return {"tenant_id":t,"foundation":v.to_dict(),"advisory_only":True}
    def detail(self,t,i):
        v=self.derive(t)["foundation"]; return v if v["foundation_id"]==i else None
