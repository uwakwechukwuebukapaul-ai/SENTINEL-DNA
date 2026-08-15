from .models import RiskLevel
class AutomationPolicy:
    def __init__(self, require_approval_above=RiskLevel.LOW): self.require_approval_above=require_approval_above
    def requires_approval(self, action): return action.requires_approval or action.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
    def allows(self, action): return action.action_type.endswith("_SIMULATION") or action.action_type in {"NOTIFY", "CREATE_TICKET", "COLLECT_EVIDENCE"}
