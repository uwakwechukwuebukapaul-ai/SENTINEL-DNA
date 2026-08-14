from .discovery import DetectionDiscoveryEngine
from .analytics import DetectionAnalytics
from .coverage import DetectionCoverage
from .recommendations import DetectionRecommendationEngine
class DetectionIntelligenceService:
 def __init__(self): self.discovery=DetectionDiscoveryEngine(); self.analytics=DetectionAnalytics(); self.coverage=DetectionCoverage(); self.recommendations=DetectionRecommendationEngine()
 def analyze(self,**kwargs):
  candidates=self.discovery.discover(**kwargs); cov=self.coverage.analyze(kwargs.get("covered",[]),kwargs.get("required",[])); return {"candidates":[c.to_dict() for c in candidates],"coverage":cov,"recommendations":self.recommendations.recommend(candidates,cov),"behavior":self.analytics.analyze(kwargs.get("investigations",[]))}
