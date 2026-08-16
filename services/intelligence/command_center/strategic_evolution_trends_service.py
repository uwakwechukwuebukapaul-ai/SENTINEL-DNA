from .governance_signal import stable_governance_signal_id
from .strategic_evolution_trends import StrategicEvolutionTrends


class StrategicEvolutionTrendsService:
    def __init__(self, evolution, improvement_trends, portfolio):
        self.evolution, self.improvement_trends, self.portfolio = evolution, improvement_trends, portfolio

    def derive(self, tenant_id):
        evolution = (self.evolution.derive(tenant_id) if self.evolution else {}).get("evolution", {})
        trends = (self.improvement_trends.derive(tenant_id) if self.improvement_trends else {}).get("trends", {})
        portfolio = (self.portfolio.derive(tenant_id) if self.portfolio else {}).get("portfolio", {})
        value = StrategicEvolutionTrends(
            tenant_id, stable_governance_signal_id(tenant_id, "strategic-evolution-trends"),
            evolution.get("convergence", "insufficient_history"), tuple(evolution.get("capability_signals", ())),
            portfolio.get("posture", "insufficient_history"), tuple(evolution.get("observed_patterns", ())),
            evolution.get("evidence_strength") or trends.get("evidence_strength", "insufficient_evidence"),
            evolution.get("confidence") or trends.get("confidence"),
            tuple(sorted(set(evolution.get("uncertainty", ())) | set(trends.get("uncertainty", ())) | set(portfolio.get("uncertainty", ())))),
            tuple(sorted(set(evolution.get("provenance", ())) | set(trends.get("provenance", ())) | set(portfolio.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "trends": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["trends"]
        return value if value["trends_id"] == signal_id else None
