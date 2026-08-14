from .ioc_fusion import IOCFusionEngine
from .confidence import IntelligenceConfidenceEngine
class ThreatFusionEngine:
 def __init__(self): self.ioc=IOCFusionEngine(); self.confidence=IntelligenceConfidenceEngine()
 def fuse(self,indicators,**kwargs):
  result=self.ioc.correlate(indicators,**kwargs); result["confidence"]=self.confidence.calculate(historical_matches=len(result["cases"])+len(result["investigations"])); return result
