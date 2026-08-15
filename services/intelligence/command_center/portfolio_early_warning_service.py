"""Deterministic early-warning interpretation; not predictive alerting."""
from .portfolio_early_warning import PortfolioEarlyWarning
from .governance_signal import stable_governance_signal_id
class PortfolioEarlyWarningService:
    def __init__(self, command_center=None): self.command_center=command_center
    def derive(self,tenant_id):
        c=self.command_center.derive(tenant_id) if self.command_center else {}; x=c.get("command_center",{}); signals=tuple(c.get("signals",())); state="insufficient_history" if x.get("governance_posture")=="insufficient_history" else "high" if x.get("governance_posture")=="governance_blocked" else "watch" if x.get("governance_posture")=="governed_with_caution" else "no_material_warning"; w=PortfolioEarlyWarning(tenant_id,stable_governance_signal_id(tenant_id,"early_warning"),state,signals,(),(),(),x.get("recurring_blockers",()),tuple(x.get("uncertainty",())),(),("Review current governance conditions; this is not a prediction of an incident.",),tuple(x.get("provenance",())),tuple(x.get("uncertainty",())),True); return {"tenant_id":tenant_id,"early_warning":w.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,warning_id):
        x=self.derive(tenant_id)["early_warning"]; return x if x["warning_id"]==warning_id else None
