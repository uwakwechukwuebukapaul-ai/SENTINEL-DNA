from .governance_signal import stable_governance_signal_id
from .intelligence_adoption_analytics import IntelligenceAdoptionAnalytics
class IntelligenceAdoptionAnalyticsService:
    def __init__(self, health, decision, maturity, summary): self.sources=(health,decision,maturity,summary)
    def derive(self,tenant_id):
        vals=[s.derive(tenant_id) if s else {} for s in self.sources]
        p=[next((v[k] for k in ("health","profile","maturity","summary") if isinstance(v.get(k),dict)),v) for v in vals]
        h,d,m,s=p; gaps=tuple(h.get("missing_intelligence_areas",()) or ())
        value=IntelligenceAdoptionAnalytics(tenant_id,stable_governance_signal_id(tenant_id,"intelligence-adoption-analytics"),"insufficient_history" if not any(p) else "advisory_coverage_available","insufficient_evidence" if not any(p) else "review_ready",gaps,tuple(m.get("maturity_gaps",()) or ()),tuple(s.get("recommended_review_areas",()) or ()),tuple(sorted({u for v in p for u in (v.get("uncertainty",()) or ())})),tuple(sorted({str(x) for v in p for x in (v.get("provenance",()) or ())})),True)
        return {"tenant_id":tenant_id,"adoption":value.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        v=self.derive(tenant_id)["adoption"]; return v if v["adoption_id"]==signal_id else None
