from .confidence_analysis import ConfidenceAnalysis
from .evidence_weighting import EvidenceWeighting
from .recommendation_analysis import RecommendationAnalysis
class DecisionIntelligenceEngine:
 def __init__(self):self.confidence=ConfidenceAnalysis();self.weighting=EvidenceWeighting();self.recommendation=RecommendationAnalysis()
 def analyze(self,context):return {'confidence':self.confidence.analyze(context),'evidence_weighting':self.weighting.weight(context),'recommendations':self.recommendation.recommend(context),'advisory_only':True}
