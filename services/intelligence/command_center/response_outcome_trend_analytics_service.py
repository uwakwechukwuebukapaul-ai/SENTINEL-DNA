from .governance_signal import stable_governance_signal_id
from .response_outcome_trend_analytics import ResponseOutcomeTrendAnalytics


class ResponseOutcomeTrendAnalyticsService:
    def __init__(self, outcomes, correlation):
        self.outcomes, self.correlation = outcomes, correlation

    def derive(self, tenant_id):
        outcomes = (self.outcomes.derive(tenant_id) if self.outcomes else {}).get("outcomes", {})
        correlation = (self.correlation.derive(tenant_id) if self.correlation else {}).get("correlation", {})
        signals = tuple(outcomes.get("observed_signals", ()))
        trend = correlation.get("relationship", "insufficient_outcomes") if signals else "insufficient_outcomes"
        result = ResponseOutcomeTrendAnalytics(
            tenant_id, stable_governance_signal_id(tenant_id, "response-outcome-trends"), trend, signals,
            "Observed response outcome trend; temporal association is not causation." if signals else "Insufficient outcomes for trend interpretation.",
            correlation.get("evidence_availability", "insufficient_outcomes"), correlation.get("confidence"),
            tuple(sorted(set(outcomes.get("uncertainty", ())) | set(correlation.get("uncertainty", ())))),
            tuple(sorted(set(outcomes.get("provenance", ())) | set(correlation.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "trends": result.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["trends"]
        return value if value["trend_id"] == signal_id else None
