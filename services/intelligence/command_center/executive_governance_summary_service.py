from .governance_signal import stable_governance_signal_id
from .executive_governance_summary import ExecutiveGovernanceSummary
class ExecutiveGovernanceSummaryService:
    def __init__(self, operating, governance, maturity, adoption): self.sources=(operating,governance,maturity,adoption)
    def derive(self,tenant_id):
        vals=[s.derive(tenant_id) if s else {} for s in self.sources]
        p=[next((v[k] for k in ("operating_model","governance","maturity","adoption") if isinstance(v.get(k),dict)),v) for v in vals]
        o,g,m,a=p
        value=ExecutiveGovernanceSummary(tenant_id,stable_governance_signal_id(tenant_id,"executive-governance-summary"),o.get("governance_readiness",g.get("portfolio_oversight_posture","insufficient_history")),m.get("ai_maturity_level","insufficient_history"),tuple(g.get("review_attention_areas",()) or ())+tuple(a.get("coverage_gaps",()) or ()),tuple(a.get("enablement_opportunities",()) or ()),tuple(sorted({u for v in p for u in (v.get("uncertainty",()) or ())})),tuple(sorted({str(x) for v in p for x in (v.get("provenance",()) or ())})),True)
        return {"tenant_id":tenant_id,"summary":value.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        v=self.derive(tenant_id)["summary"]; return v if v["summary_id"]==signal_id else None
