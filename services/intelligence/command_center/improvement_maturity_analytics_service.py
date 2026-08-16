from .governance_signal import stable_governance_signal_id
from .improvement_maturity_analytics import ImprovementMaturityAnalytics


class ImprovementMaturityAnalyticsService:
    def __init__(self, maturity, evolution, trends):
        self.maturity, self.evolution, self.trends = maturity, evolution, trends

    def derive(self, tenant_id):
        maturity = (self.maturity.derive(tenant_id) if self.maturity else {}).get("maturity", {})
        evolution = (self.evolution.derive(tenant_id) if self.evolution else {}).get("evolution", {})
        trends = (self.trends.derive(tenant_id) if self.trends else {}).get("trends", {})
        posture = maturity.get("posture", "insufficient_history")
        trend = maturity.get("trend", "insufficient_history")
        interpretation = "Observed maturity progression is presented as advisory interpretation; no causal relationship is established." if trend and not trend.startswith("insufficient") else "Insufficient history for maturity progression interpretation; no causal relationship is established."
        value = ImprovementMaturityAnalytics(
            tenant_id, stable_governance_signal_id(tenant_id, "improvement-maturity-analytics"), posture, interpretation,
            tuple(maturity.get("capability_evolution", ())) or tuple(evolution.get("capability_signals", ())),
            tuple(trends.get("observed_patterns", ())), trend,
            maturity.get("evidence_strength") or evolution.get("evidence_strength", "insufficient_evidence"),
            maturity.get("confidence") or evolution.get("confidence"),
            tuple(sorted(set(maturity.get("uncertainty", ())) | set(evolution.get("uncertainty", ())) | set(trends.get("uncertainty", ())))),
            tuple(sorted(set(maturity.get("provenance", ())) | set(evolution.get("provenance", ())) | set(trends.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "analytics": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["analytics"]
        return value if value["analytics_id"] == signal_id else None
