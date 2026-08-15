from .models import InvestigationPlanScore
class PlanOptimizer:
    def score(self, tenant_id, plan_id, recommendations, previous=None):
        unnecessary=sum(item.unnecessary for item in recommendations); efficiency=round(max(0.0, min(1.0, (len(recommendations)-unnecessary)/max(1,len(recommendations)))),2); return InvestigationPlanScore(plan_id, tenant_id, efficiency, len(recommendations)-unnecessary, "Advisory score based on ordered, non-duplicate investigation steps")
