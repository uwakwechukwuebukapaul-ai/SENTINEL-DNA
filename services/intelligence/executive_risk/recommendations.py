from .models import BusinessRiskFinding
class ExecutiveRecommendations:
    def generate(self,tenant_id,asset,score):
        if score<60:return []
        level="critical" if score>=80 else "high"; return [BusinessRiskFinding(tenant_id=tenant_id,asset_id=asset.asset_id,severity=level,explanation="Business asset has elevated combined security and business impact.",recommendation="Review executive risk treatment, ownership, and prioritization with human stakeholders.")]
