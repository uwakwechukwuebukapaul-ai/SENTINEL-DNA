from .governance_signal import stable_governance_signal_id
from .improvement_maturity import ImprovementMaturity


class ImprovementMaturityService:
    def __init__(self, governance, evolution, continuous):
        self.governance, self.evolution, self.continuous = governance, evolution, continuous

    def derive(self, tenant_id):
        governance = (self.governance.derive(tenant_id) if self.governance else {}).get("governance", {})
        evolution = (self.evolution.derive(tenant_id) if self.evolution else {}).get("evolution", {})
        continuous = (self.continuous.derive(tenant_id) if self.continuous else {}).get("continuous_improvement", {})
        signals = tuple(governance.get("priorities", ())) + tuple(evolution.get("capability_signals", ()))
        value = ImprovementMaturity(
            tenant_id, stable_governance_signal_id(tenant_id, "improvement-maturity"),
            governance.get("portfolio_posture", "insufficient_history"), signals,
            tuple(evolution.get("capability_signals", ())), continuous.get("readiness", "insufficient_evidence"),
            evolution.get("improvement_trend", "insufficient_history"),
            governance.get("evidence_strength") or evolution.get("evidence_strength", "insufficient_evidence"),
            governance.get("confidence") or evolution.get("confidence"),
            tuple(sorted(set(governance.get("uncertainty", ())) | set(evolution.get("uncertainty", ())) | set(continuous.get("uncertainty", ())))),
            tuple(sorted(set(governance.get("provenance", ())) | set(evolution.get("provenance", ())) | set(continuous.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "maturity": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["maturity"]
        return value if value["maturity_id"] == signal_id else None
