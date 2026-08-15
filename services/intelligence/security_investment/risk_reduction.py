from .models import RiskReductionEstimate
class RiskReductionEngine:
    def estimate(self,tenant_id,opportunity,current_risk,expected_effectiveness=None):
        target=expected_effectiveness if expected_effectiveness is not None else max(opportunity.current_control_effectiveness,.8); projected=round(current_risk*(1-target),2); return RiskReductionEstimate(tenant_id=tenant_id,opportunity_id=opportunity.opportunity_id,current_risk=current_risk,projected_risk=projected,reduction=round(current_risk-projected,2),confidence=.7)
