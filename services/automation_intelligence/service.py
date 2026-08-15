from uuid import uuid4
from .models import AutomationExperience
from .repository import AutomationIntelligenceRepository
from .performance import PerformanceEngine
from .learning import AutomationLearning
from .optimizer import PlaybookOptimizer
from .recommendations import RecommendationEngine
from .memory import AutomationMemory
class AutomationIntelligenceService:
    def __init__(self,repository=None,audit=None):
        self.repository=repository or AutomationIntelligenceRepository(); self.performance=PerformanceEngine(); self.learning=AutomationLearning(); self.optimizer=PlaybookOptimizer(); self.recommendations=RecommendationEngine(); self.memory=AutomationMemory(self.repository); self.audit=audit
    def record_experience(self, tenant_id, workflow_id, incident_type="unknown", severity="medium", outcome="unknown", approval_decision="unknown", analyst_feedback=""):
        x=AutomationExperience(str(uuid4()),tenant_id,workflow_id,incident_type,severity,outcome,approval_decision,analyst_feedback); self.repository.save_experience(x); self._audit("automation_experience_recorded",tenant_id,workflow_id=workflow_id); return x
    def measure_performance(self, tenant_id, workflow_id): return self.performance.calculate(tenant_id,workflow_id,self.repository.list_experiences(tenant_id,workflow_id))
    calculate_performance=measure_performance
    def learn(self, tenant_id, workflow_id): return self.learning.summarize(self.repository.list_experiences(tenant_id,workflow_id))
    def recommend_improvements(self, tenant_id, workflow_id):
        result=self.recommendations.filter_advisory(self.optimizer.recommend(tenant_id,workflow_id,self.measure_performance(tenant_id,workflow_id)))
        for item in result: self.repository.save_recommendation(item)
        self._audit("automation_recommendations_generated",tenant_id,workflow_id=workflow_id,count=len(result)); return result
    def similar_experiences(self,tenant_id,incident_type,severity): return self.memory.similar(tenant_id,incident_type,severity)
    def _audit(self,event,tenant_id,**details):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,tenant_id=tenant_id,**details)
