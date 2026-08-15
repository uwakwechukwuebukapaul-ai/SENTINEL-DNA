"""Deterministic advisory policy review over canonical forecast governance."""
from .forecast_policy_review import ForecastPolicyReview, stable_policy_review_id

class ForecastPolicyReviewService:
    def __init__(self, governance_service=None): self.governance_service = governance_service

    def derive(self, tenant_id):
        g = self.governance_service.derive(tenant_id) if self.governance_service else {}
        status = g.get("governance_status", "insufficient_evidence")
        reliability = (g.get("reliability_trend") or {}).get("trend")
        calibration = (g.get("calibration_trend") or {}).get("status")
        drift = (g.get("drift_trend") or {}).get("status") or (g.get("drift_trend") or {}).get("classification")
        risk = (g.get("risk_trend") or {}).get("status")
        uncertainty = tuple(sorted(set(g.get("uncertainty") or ())))
        blockers = []
        if status == "insufficient_evidence" or "insufficient_history" in uncertainty:
            blockers.append("insufficient_historical_evaluation")
        if status == "high_risk": blockers.append("elevated_governance_risk")
        if calibration in {"concern", "poor", "weak"}: blockers.append("calibration_concern")
        if drift in {"elevated", "significant", "high"}: blockers.append("significant_drift")
        if not g.get("provenance"): blockers.append("missing_provenance")
        blockers = tuple(sorted(set(blockers)))
        readiness = "insufficient_history" if "insufficient_historical_evaluation" in blockers else "review_blocked" if blockers else "review_with_caution" if status == "watch" or uncertainty else "review_ready"
        review = ForecastPolicyReview(tenant_id, stable_policy_review_id(tenant_id, "policy_review", "portfolio_forecast"), None, None, None, readiness, readiness, reliability, calibration, drift, risk, g.get("evidence_strength"), g.get("confidence"), uncertainty, tuple(g.get("provenance") or ("forecast_governance",)), tuple(x.get("stable_id") for x in g.get("governance_signals", ())), tuple(blockers) or ("Governance conditions support bounded executive review.",), ("Policy readiness is not forecast correctness.", "Review remains advisory and human-controlled."), ("Forecast outputs are not observed outcomes.", "No causal inference or decision execution."), ("review supporting evidence", "review uncertainty before executive use") if readiness != "review_ready" else ("continue monitoring forecast reliability",), "derived")
        return {"tenant_id": tenant_id, "policy_review": review.to_dict(), "governance": g, "governance_blockers": list(blockers), "advisory_only": True}

    def detail(self, tenant_id, signal_id):
        value = self.derive(tenant_id)["policy_review"]
        return value if value["review_id"] == signal_id else None
