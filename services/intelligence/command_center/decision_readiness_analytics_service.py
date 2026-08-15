"""Deterministic longitudinal readiness analytics without fabricated history."""
from .decision_readiness_analytics import DecisionReadinessAnalytics
from .forecast_policy_analytics import stable_policy_analytics_id
class DecisionReadinessAnalyticsService:
    def __init__(self, readiness_service=None): self.readiness_service=readiness_service
    def derive(self,tenant_id):
        r=self.readiness_service.derive(tenant_id) if self.readiness_service else {}; x=r.get("readiness",{}); limited="insufficient_history" if not x else "limited_history"
        a=DecisionReadinessAnalytics(tenant_id,stable_policy_analytics_id(tenant_id,"readiness_analytics"),"insufficient_history",(),tuple(x.get("governance_blockers",())),(),(),(),(),(),tuple(x.get("uncertainty",())),x.get("confidence"),tuple(x.get("uncertainty",())),tuple(x.get("provenance",())),limited,True)
        return {"tenant_id":tenant_id,"analytics":a.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        x=self.derive(tenant_id)["analytics"]; return x if x["analytics_id"]==signal_id else None
