"""Deterministic analytics over the current canonical policy review."""
from collections import Counter
from .forecast_policy_analytics import ForecastPolicyAnalytics, stable_policy_analytics_id
from .forecast_governance_trends import ForecastGovernanceTrend
class ForecastPolicyAnalyticsService:
    def __init__(self, policy_review_service=None): self.policy_review_service=policy_review_service
    def derive(self, tenant_id):
        p=self.policy_review_service.derive(tenant_id) if self.policy_review_service else {}; review=p.get("policy_review",{}); g=p.get("governance",{}); blockers=tuple(sorted(p.get("governance_blockers",()))); status="limited_history" if review else "insufficient_history"; refs=tuple(sorted(review.get("contributing_references",())))
        model=ForecastPolicyAnalytics(tenant_id,stable_policy_analytics_id(tenant_id,"policy"), (review.get("review_id"),) if review.get("review_id") else (), (), tuple(g.get("provenance",())), review.get("policy_readiness","insufficient_history"),review.get("policy_readiness","insufficient_history"),{review.get("policy_readiness","insufficient_history"):1},Counter(blockers),{str((g.get("reliability_trend") or {}).get("trend")):1},{str((g.get("calibration_trend") or {}).get("status")):1},{str((g.get("drift_trend") or {}).get("status","unavailable")):1},{str((g.get("risk_trend") or {}).get("status","unavailable")):1},review.get("confidence"),review.get("evidence_strength"),tuple(sorted(review.get("uncertainty",()))),tuple(sorted(set(review.get("provenance",())))),refs,"current_period",status,True)
        return {"tenant_id":tenant_id,"analytics":model.to_dict(),"governance_trends":ForecastGovernanceTrend(tenant_id,stable_policy_analytics_id(tenant_id,"trend"),"insufficient_history", "insufficient_history", "insufficient_history", "insufficient_history", "insufficient_history", (), model.uncertainty, model.provenance).to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        x=self.derive(tenant_id)["analytics"]; return x if x["analytics_id"]==signal_id else None
