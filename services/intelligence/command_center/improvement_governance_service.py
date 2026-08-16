from .governance_signal import stable_governance_signal_id
from .improvement_governance import ImprovementGovernance


class ImprovementGovernanceService:
    def __init__(self, portfolio, trends):
        self.portfolio, self.trends = portfolio, trends

    def derive(self, tenant_id):
        portfolio = (self.portfolio.derive(tenant_id) if self.portfolio else {}).get("portfolio", {})
        trends = (self.trends.derive(tenant_id) if self.trends else {}).get("analytics", {})
        value = ImprovementGovernance(
            tenant_id, stable_governance_signal_id(tenant_id, "improvement-governance"),
            portfolio.get("posture", "insufficient_history"),
            tuple(portfolio.get("strategic_focus_areas", ())) or tuple(portfolio.get("improvement_themes", ())),
            trends.get("trend", "insufficient_evidence"), tuple(portfolio.get("unresolved_areas", ())),
            portfolio.get("evidence_strength") or trends.get("evidence_strength", "insufficient_evidence"),
            portfolio.get("confidence") or trends.get("confidence"),
            tuple(sorted(set(portfolio.get("uncertainty", ())) | set(trends.get("uncertainty", ())))),
            tuple(sorted(set(portfolio.get("provenance", ())) | set(trends.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "governance": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["governance"]
        return value if value["governance_id"] == signal_id else None
