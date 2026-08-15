from .models import OptimizationResult
from .optimizer import PlanOptimizer
from .planner import InvestigationPlanAdvisor
from .repository import InvestigationOptimizationRepository

class InvestigationOptimizationService:
    def __init__(self, tenant_id=None, repository=None): self.tenant_id=tenant_id; self.repository=repository or InvestigationOptimizationRepository(); self.advisor=InvestigationPlanAdvisor(); self.optimizer=PlanOptimizer()
    def optimize_plan(self, plan_id, steps, previous_investigations=None):
        recommendations=self.advisor.recommend(steps); score=self.optimizer.score(self.tenant_id, plan_id, recommendations, previous_investigations); comparison=self.compare_investigations(previous_investigations or []); return self.repository.save(OptimizationResult(self.tenant_id, score, recommendations, comparison), plan_id)
    def recommend_steps(self, steps): return self.advisor.recommend(steps)
    def compare_investigations(self, investigations):
        items=list(investigations or []); return {"historical_count": len(items), "average_steps": sum(len(item.get("steps", [])) for item in items)/len(items) if items else 0}
