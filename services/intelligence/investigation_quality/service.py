from .benchmark import QualityBenchmarkEngine
from .quality import InvestigationQualityEngine
from .recommendations import QualityRecommendationEngine
from .repository import InvestigationQualityRepository

class InvestigationQualityService:
    def __init__(self, tenant_id=None, repository=None, audit_logger=None): self.tenant_id=tenant_id; self.repository=repository or InvestigationQualityRepository(); self.audit_logger=audit_logger; self.quality=InvestigationQualityEngine(); self.benchmark=QualityBenchmarkEngine(); self.recommendation=QualityRecommendationEngine()
    def _audit(self,event,**payload):
        if self.audit_logger and hasattr(self.audit_logger,"record"): self.audit_logger.record(event,tenant_id=self.tenant_id,**payload)
    def assess_investigation(self, investigation_id, result):
        assessment=self.repository.save_assessment(self.quality.assess(investigation_id,self.tenant_id,result)); self._audit("investigation_quality_assessed",investigation_id=investigation_id,score=assessment.overall_score); return assessment
    def benchmark_quality(self): return self.benchmark.benchmark(self.tenant_id,self.repository.list_assessments(self.tenant_id))
    def generate_recommendations(self, investigation_id):
        assessment=self.repository.get_assessment(self.tenant_id,investigation_id); return self.recommendation.generate(assessment) if assessment else []
