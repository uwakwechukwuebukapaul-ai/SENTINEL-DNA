from .governance_optimization_analytics import GovernanceOptimizationAnalytics
from .governance_signal import stable_governance_signal_id


class GovernanceOptimizationAnalyticsService:
    def __init__(self, optimization, governance, continuous):
        self.optimization, self.governance, self.continuous = optimization, governance, continuous

    def derive(self, tenant_id):
        optimization = (self.optimization.derive(tenant_id) if self.optimization else {}).get("optimization", {})
        governance = (self.governance.derive(tenant_id) if self.governance else {}).get("governance", {})
        continuous = (self.continuous.derive(tenant_id) if self.continuous else {}).get("continuous_improvement", {})
        value = GovernanceOptimizationAnalytics(
            tenant_id, stable_governance_signal_id(tenant_id, "governance-optimization-analytics"),
            optimization.get("posture", "insufficient_evidence"),
            tuple(continuous.get("opportunities", ())) or tuple(governance.get("priorities", ())),
            continuous.get("readiness", "insufficient_evidence"),
            optimization.get("evidence_strength", "insufficient_evidence"), optimization.get("confidence"),
            tuple(sorted(set(optimization.get("uncertainty", ())) | set(governance.get("uncertainty", ())) | set(continuous.get("uncertainty", ())))),
            tuple(sorted(set(optimization.get("provenance", ())) | set(governance.get("provenance", ())) | set(continuous.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "analytics": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["analytics"]
        return value if value["analytics_id"] == signal_id else None
