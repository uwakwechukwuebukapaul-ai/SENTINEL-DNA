from .models import LearningInsight, stable_id
from .pattern_analysis import PatternAnalysis
from .quality_analysis import QualityAnalysis
class InvestigationLearningService:
    def __init__(self, context_provider=None): self.context_provider=context_provider
    def derive(self, tenant_id, context=None):
        context=context or (self.context_provider(tenant_id) if self.context_provider else {})
        p=PatternAnalysis().analyze(context); q=QualityAnalysis().analyze(context)
        return LearningInsight(stable_id(tenant_id,"investigation-learning"),tenant_id,p["patterns"],tuple(context.get("evidence_sources",())),p["confidence"],tuple(context.get("provenance",())),p["uncertainty"],(q["quality_trend"],),True).to_dict()
