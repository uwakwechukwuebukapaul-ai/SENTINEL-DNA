from .governance_learning_optimization import GovernanceLearningOptimization
from .governance_signal import stable_governance_signal_id


class GovernanceLearningOptimizationService:
    def __init__(self, continuous_improvement, outcome_learning, improvement_trends):
        self.continuous_improvement = continuous_improvement
        self.outcome_learning = outcome_learning
        self.improvement_trends = improvement_trends

    def derive(self, tenant_id):
        continuous = (self.continuous_improvement.derive(tenant_id) if self.continuous_improvement else {}).get("continuous_improvement", {})
        learning = (self.outcome_learning.derive(tenant_id) if self.outcome_learning else {}).get("outcome_learning", {})
        trends = (self.improvement_trends.derive(tenant_id) if self.improvement_trends else {}).get("trends", {})
        signals = tuple(learning.get("learning_signals", ())) or tuple(continuous.get("learning_priorities", ()))
        considerations = tuple(continuous.get("next_step_considerations", ()))
        value = GovernanceLearningOptimization(
            tenant_id, stable_governance_signal_id(tenant_id, "governance-learning-optimization"),
            continuous.get("readiness", "insufficient_evidence"), signals, considerations,
            continuous.get("evidence_strength") or trends.get("evidence_strength", "insufficient_evidence"),
            continuous.get("confidence") or trends.get("confidence"),
            tuple(sorted(set(continuous.get("uncertainty", ())) | set(learning.get("uncertainty", ())) | set(trends.get("uncertainty", ())))),
            tuple(sorted(set(continuous.get("provenance", ())) | set(learning.get("provenance", ())) | set(trends.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "optimization": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["optimization"]
        return value if value["optimization_id"] == signal_id else None
