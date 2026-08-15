"""Deterministic executive context; never records an executive decision."""
from .decision_oversight import DecisionOversight, stable_oversight_id

class DecisionOversightService:
    def __init__(self, policy_review_service=None): self.policy_review_service = policy_review_service
    def derive(self, tenant_id):
        p = self.policy_review_service.derive(tenant_id) if self.policy_review_service else {"policy_review": {}, "governance_blockers": []}
        review = p.get("policy_review", {}); blockers = tuple(p.get("governance_blockers", ()))
        posture = "blocked" if blockers else "caution" if review.get("policy_readiness") == "review_with_caution" else "reviewable"
        result = DecisionOversight(tenant_id, stable_oversight_id(tenant_id, "decision_oversight", "portfolio_forecast"), review.get("forecast_reference"), review.get("review_id"), review.get("portfolio_reference"), posture, review.get("policy_readiness", "insufficient_evidence"), tuple(blockers), (), blockers, ("Compare forecast evaluation with observed outcomes when history exists.",), tuple(review.get("uncertainty", ())), (), (), (), ("Review governance blockers before strategic reliance.",), tuple(review.get("provenance", ())), "insufficient_decision_history")
        return {"tenant_id": tenant_id, "decision_oversight": result.to_dict(), "policy_review": p, "advisory_only": True}
    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["decision_oversight"]
        return value if value["oversight_id"] == signal_id else None
