"""History analytics with explicit no-history semantics."""
from .governance_posture_analytics import GovernancePostureAnalytics
from .governance_signal import stable_governance_signal_id
class GovernancePostureAnalyticsService:
    def __init__(self, command_center=None): self.command_center=command_center
    def derive(self,tenant_id):
        c=self.command_center.derive(tenant_id) if self.command_center else {}; x=c.get("command_center",{}); a=GovernancePostureAnalytics(tenant_id,stable_governance_signal_id(tenant_id,"history"),"insufficient_history",(),tuple(x.get("recurring_blockers",())),(),(),(),(),tuple(x.get("uncertainty",())),x.get("confidence"),tuple(x.get("uncertainty",())),tuple(x.get("provenance",())),x.get("temporal_coverage","unavailable"),True); return {"tenant_id":tenant_id,"history":a.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        x=self.derive(tenant_id)["history"]; return x if x["analytics_id"]==signal_id else None
