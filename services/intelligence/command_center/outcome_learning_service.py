from .governance_signal import stable_governance_signal_id
from .outcome_learning import OutcomeLearning


class OutcomeLearningService:
    def __init__(self, outcomes, learning, correlation):
        self.outcomes, self.learning, self.correlation = outcomes, learning, correlation

    def derive(self, tenant_id):
        outcomes = (self.outcomes.derive(tenant_id) if self.outcomes else {}).get("outcomes", {})
        learning = (self.learning.derive(tenant_id) if self.learning else {}).get("learning", {})
        correlation = (self.correlation.derive(tenant_id) if self.correlation else {}).get("correlation", {})
        observed = tuple(outcomes.get("observed_signals", ()))
        value = OutcomeLearning(
            tenant_id, stable_governance_signal_id(tenant_id, "outcome-learning"),
            outcomes.get("outcome_state", "unknown") if observed else "insufficient_outcomes", observed,
            tuple(learning.get("recurring_patterns", ())), tuple(learning.get("recurring_patterns", ())),
            tuple(correlation.get("candidates", ())),
            outcomes.get("evidence_strength") or correlation.get("evidence_availability", "insufficient_outcomes"),
            outcomes.get("confidence") or correlation.get("confidence"),
            tuple(sorted(set(outcomes.get("uncertainty", ())) | set(learning.get("uncertainty", ())) | set(correlation.get("uncertainty", ())))),
            tuple(sorted(set(outcomes.get("provenance", ())) | set(learning.get("provenance", ())) | set(correlation.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "outcome_learning": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["outcome_learning"]
        return value if value["learning_id"] == signal_id else None
