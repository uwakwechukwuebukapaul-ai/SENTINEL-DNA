from .governance_signal import stable_governance_signal_id
from .strategic_portfolio_governance import StrategicPortfolioGovernance
class StrategicPortfolioGovernanceService:
    def __init__(self, portfolio, forecast, command_center): self.sources=(portfolio,forecast,command_center)
    def derive(self,tenant_id):
        vals=[s.derive(tenant_id) if s else {} for s in self.sources]
        p=[next((v[k] for k in ("portfolio","forecast","command_center") if isinstance(v.get(k),dict)),v) for v in vals]
        portfolio,forecast,cc=p
        value=StrategicPortfolioGovernance(tenant_id,stable_governance_signal_id(tenant_id,"strategic-portfolio-governance"),portfolio.get("posture",forecast.get("posture", "insufficient_history")),tuple(portfolio.get("signals",portfolio.get("portfolio_signals",())) or ()),"visible" if portfolio else "insufficient_history",tuple(portfolio.get("maturity_indicators",()) or ()),tuple(cc.get("executive_attention_areas",()) or ()),portfolio.get("evidence_strength", "insufficient_evidence"),tuple(sorted({u for v in p for u in (v.get("uncertainty",()) or ())})),tuple(sorted({str(x) for v in p for x in (v.get("provenance",()) or ())})),True)
        return {"tenant_id":tenant_id,"governance":value.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        v=self.derive(tenant_id)["governance"]; return v if v["governance_id"]==signal_id else None
