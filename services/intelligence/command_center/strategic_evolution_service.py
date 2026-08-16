from .governance_signal import stable_governance_signal_id
from .strategic_evolution import StrategicEvolution


class StrategicEvolutionService:
    def __init__(self, improvement_trends, optimization, governance):
        self.improvement_trends, self.optimization, self.governance = improvement_trends, optimization, governance

    def derive(self, tenant_id):
        trends = (self.improvement_trends.derive(tenant_id) if self.improvement_trends else {}).get("trends", {})
        optimization = (self.optimization.derive(tenant_id) if self.optimization else {}).get("optimization", {})
        governance = (self.governance.derive(tenant_id) if self.governance else {}).get("governance", {})
        trend_values = [trends.get("improvement_trend"), trends.get("governance_learning_trend"), trends.get("response_outcome_trend")]
        known = [value for value in trend_values if value and not value.startswith("insufficient")]
        convergence = "converging" if len(set(known)) == 1 and known else ("mixed_signals" if known else "insufficient_history")
        patterns = tuple(trends.get("observed_patterns", ()))
        value = StrategicEvolution(
            tenant_id, stable_governance_signal_id(tenant_id, "strategic-evolution"),
            governance.get("portfolio_posture", "insufficient_history"), trends.get("improvement_trend", "insufficient_history"),
            trends.get("governance_learning_trend", "insufficient_history"), trends.get("response_outcome_trend", "insufficient_outcomes"),
            convergence, tuple(optimization.get("learning_signals", ())), patterns,
            "Observed trend convergence is presented as advisory interpretation, not causation." if known else "Insufficient history for strategic evolution interpretation; no causal relationship is established.",
            optimization.get("evidence_strength") or trends.get("evidence_strength", "insufficient_evidence"),
            optimization.get("confidence") or trends.get("confidence"),
            tuple(sorted(set(trends.get("uncertainty", ())) | set(optimization.get("uncertainty", ())) | set(governance.get("uncertainty", ())))),
            tuple(sorted(set(trends.get("provenance", ())) | set(optimization.get("provenance", ())) | set(governance.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "evolution": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["evolution"]
        return value if value["evolution_id"] == signal_id else None
