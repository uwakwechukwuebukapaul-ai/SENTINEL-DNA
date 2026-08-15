from .governance_learning_correlation import GovernanceLearningCorrelation
from .governance_signal import stable_governance_signal_id


class GovernanceLearningCorrelationService:
    def __init__(self, learning, correlation):
        self.learning, self.correlation = learning, correlation

    def derive(self, tenant_id):
        learning = (self.learning.derive(tenant_id) if self.learning else {}).get("learning", {})
        correlation = (self.correlation.derive(tenant_id) if self.correlation else {}).get("correlation", {})
        result = GovernanceLearningCorrelation(
            tenant_id, stable_governance_signal_id(tenant_id, "governance-learning-correlation"),
            correlation.get("relationship", "insufficient_history"),
            tuple(learning.get("recurring_patterns", ())), tuple(correlation.get("candidates", ())),
            "Observed temporal association only; no causal relationship is established.",
            correlation.get("evidence_availability", "insufficient_evidence"), correlation.get("confidence"),
            tuple(sorted(set(learning.get("uncertainty", ())) | set(correlation.get("uncertainty", ())))),
            tuple(sorted(set(learning.get("provenance", ())) | set(correlation.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "correlation": result.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["correlation"]
        return value if value["correlation_id"] == signal_id else None
