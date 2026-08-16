from .governance_signal import stable_governance_signal_id
from .strategic_evolution_command_center import StrategicEvolutionCommandCenter


class StrategicEvolutionCommandCenterService:
    def __init__(self, evolution, optimization, maturity, continuous):
        self.evolution, self.optimization, self.maturity, self.continuous = evolution, optimization, maturity, continuous

    def derive(self, tenant_id):
        evolution = (self.evolution.derive(tenant_id) if self.evolution else {}).get("evolution", {})
        optimization = (self.optimization.derive(tenant_id) if self.optimization else {}).get("optimization", {})
        maturity = (self.maturity.derive(tenant_id) if self.maturity else {}).get("maturity", {})
        continuous = (self.continuous.derive(tenant_id) if self.continuous else {}).get("continuous_improvement", {})
        signals = tuple(evolution.get("capability_signals", ())) + tuple(continuous.get("opportunities", ()))
        context = tuple(optimization.get("optimization_considerations", ())) + tuple(continuous.get("next_step_considerations", ()))
        value = StrategicEvolutionCommandCenter(
            tenant_id, stable_governance_signal_id(tenant_id, "strategic-evolution-command-center"),
            evolution.get("posture", "insufficient_history"), evolution.get("convergence", "insufficient_history"),
            optimization.get("posture", "insufficient_evidence"), maturity.get("posture", "insufficient_history"),
            signals, context,
            evolution.get("evidence_strength") or optimization.get("evidence_strength", "insufficient_evidence"),
            evolution.get("confidence") or optimization.get("confidence"),
            tuple(sorted(set(evolution.get("uncertainty", ())) | set(optimization.get("uncertainty", ())) | set(maturity.get("uncertainty", ())) | set(continuous.get("uncertainty", ())))),
            tuple(sorted(set(evolution.get("provenance", ())) | set(optimization.get("provenance", ())) | set(maturity.get("provenance", ())) | set(continuous.get("provenance", ())))), True,
        )
        return {"tenant_id": tenant_id, "command_center": value.to_dict(), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["command_center"]
        return value if value["command_center_id"] == signal_id else None
