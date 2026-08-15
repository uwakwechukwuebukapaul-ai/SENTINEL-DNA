from .scoring import QualityScoringEngine
class InvestigationQualityEngine:
    def __init__(self): self.scorer=QualityScoringEngine()
    def assess(self, investigation_id, tenant_id, result): return self.scorer.assess(investigation_id, tenant_id, result)
