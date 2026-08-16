from .governance_signal import stable_governance_signal_id
from .improvement_trends import ImprovementTrends


class ImprovementTrendsService:
    def __init__(self, portfolio, learning_trends, outcome_trends):
        self.portfolio, self.learning_trends, self.outcome_trends = portfolio, learning_trends, outcome_trends

    def derive(self, tenant_id):
        portfolio = (self.portfolio.derive(tenant_id) if self.portfolio else {}).get("portfolio", {})
        learning = (self.learning_trends.derive(tenant_id) if self.learning_trends else {}).get("analytics", {})
        outcomes = (self.outcome_trends.derive(tenant_id) if self.outcome_trends else {}).get("trends", {})
        patterns = tuple(learning.get("recurring_themes", ())) + tuple(outcomes.get("outcome_signals", ()))
        value = ImprovementTrends(
            tenant_id, stable_governance_signal_id(tenant_id, "improvement-trends"),
            portfolio.get("posture", "insufficient_history") if portfolio else "insufficient_history",
            learning.get("trend", "insufficient_history"), outcomes.get("trend", "insufficient_outcomes"),
            portfolio.get("posture", "insufficient_history"), patterns,
            "Observed trends are available for advisory review; no causal claim is made." if patterns else "Insufficient history for longitudinal interpretation.",
            portfolio.get("evidence_strength") or learning.get("evidence_strength") or outcomes.get("evidence_strength", "insufficient_evidence"),
            portfolio.get("confidence") or learning.get("confidence") or outcomes.get("confidence"),
            tuple(sorted(set(portfolio.get("uncertainty", ())) | set(learning.get("uncertainty", ())) | set(outcomes.get("uncertainty", ())))),
            tuple(sorted(set(portfolio.get("provenance", ())) | set(learning.get("provenance", ())) | set(outcomes.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "trends": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["trends"]
        return value if value["trends_id"] == signal_id else None
