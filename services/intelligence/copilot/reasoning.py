from .confidence import ConfidenceEngine
from .explanation import ExplanationEngine
from .recommendation import RecommendationEngine
class CopilotReasoningEngine:
    def __init__(self): self.confidence=ConfidenceEngine();self.explanation=ExplanationEngine();self.recommendation=RecommendationEngine()
    def reason(self,context): return {'explanation':self.explanation.explain(context),'recommendations':self.recommendation.recommend(context),'confidence':self.confidence.assess(context),'provenance':context.provenance,'advisory_only':True}
