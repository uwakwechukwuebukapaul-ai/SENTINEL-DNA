"""Deterministic decision-readiness classification over policy review and oversight."""
from .decision_readiness import DecisionReadiness
from .forecast_policy_analytics import stable_policy_analytics_id
class DecisionReadinessService:
    def __init__(self, policy_review_service=None, oversight_service=None): self.policy_review_service=policy_review_service; self.oversight_service=oversight_service
    def derive(self,tenant_id):
        p=self.policy_review_service.derive(tenant_id) if self.policy_review_service else {}; r=p.get("policy_review",{}); o=self.oversight_service.derive(tenant_id) if self.oversight_service else {}; d=o.get("decision_oversight",{}); blockers=tuple(p.get("governance_blockers",()))
        readiness="insufficient_history" if r.get("policy_readiness") in {None,"insufficient_history"} else "decision_review_blocked" if blockers else "decision_review_with_caution" if r.get("policy_readiness")!="review_ready" else "decision_ready_for_review"
        x=DecisionReadiness(tenant_id=tenant_id, readiness_id=stable_policy_analytics_id(tenant_id,"readiness"), readiness_classification=readiness, policy_review_status=r.get("policy_readiness","insufficient_history"), governance_status=(p.get("governance") or {}).get("governance_status","insufficient_evidence"), reliability=r.get("reliability_state"), calibration=r.get("calibration_state"), drift=r.get("drift_state"), risk_monitoring=r.get("risk_monitoring_state"), evidence_strength=r.get("evidence_strength"), confidence=r.get("confidence"), uncertainty=tuple(r.get("uncertainty",())), governance_blockers=blockers, planning_references=tuple(d.get("strategic_planning_references",())), recommendations=tuple(r.get("advisory_recommendations",())), provenance=tuple(r.get("provenance",())), decision_history_status=d.get("decision_history_status","insufficient_decision_history"))
        return {"tenant_id":tenant_id,"readiness":x.to_dict(),"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        x=self.derive(tenant_id)["readiness"]; return x if x["readiness_id"]==signal_id else None
