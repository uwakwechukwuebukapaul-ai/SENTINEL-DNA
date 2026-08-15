from uuid import uuid4
from .repository import SecurityInvestmentRepository
from .prioritization import InvestmentPrioritizer
from .risk_reduction import RiskReductionEngine
from .aggregation import InvestmentAggregator
from .recommendations import InvestmentRecommendations
class SecurityInvestmentService:
    def __init__(self,repository=None,audit=None): self.repository=repository or SecurityInvestmentRepository(); self.prioritizer=InvestmentPrioritizer(); self.reduction=RiskReductionEngine(); self.aggregation=InvestmentAggregator(); self.recommendations=InvestmentRecommendations(); self.audit=audit
    def register_opportunity(self,opportunity): return self.repository.save_opportunity(opportunity)
    def prioritize(self,tenant_id,risk_by_opportunity=None,impact_by_opportunity=None):
        risk_by_opportunity=risk_by_opportunity or {}; impact_by_opportunity=impact_by_opportunity or {}; items=[{"opportunity":x,"score":self.prioritizer.score(x,risk_by_opportunity.get(x.opportunity_id,0),impact_by_opportunity.get(x.opportunity_id,0))} for x in self.repository.list_opportunities(tenant_id)]; result=self.prioritizer.prioritize(tenant_id,items)
        for x in result:self.repository.save_priority(x)
        return self.recommendations.generate(result)
    def estimate_reduction(self,tenant_id,opportunity_id,current_risk,expected_effectiveness=None):
        opportunity=self.repository.get_opportunity(opportunity_id,tenant_id)
        if not opportunity:return None
        result=self.reduction.estimate(tenant_id,opportunity,current_risk,expected_effectiveness); self.repository.save_estimate(result); return result
    def summary(self,tenant_id): return self.aggregation.summarize(self.repository.list_opportunities(tenant_id),[])
