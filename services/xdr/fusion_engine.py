from .models import SecuritySignal,XDRIncident
from .correlation import CorrelationEngine
from .risk_engine import XDRRiskEngine
from .attack_story import AttackStoryGenerator
class XDRFusionEngine:
 def __init__(self,repository): self.repository=repository; self.correlation=CorrelationEngine(); self.risk=XDRRiskEngine(); self.story=AttackStoryGenerator()
 def ingest(self,org,data):
  signal=SecuritySignal(org,data.get("source","unknown"),data.get("signal_type","DETECTION_ALERT"),data.get("severity","MEDIUM"),data.get("entity","unknown"),data.get("entity_type","UNKNOWN"),data.get("timestamp",""),data.get("metadata",{}),float(data.get("confidence",.8))); self.repository.add_signal(signal); return signal
 def fuse(self,org):
  incidents=[]
  for group in self.correlation.correlate(self.repository.scoped(self.repository.signals,org)):
   risk=self.risk.calculate(group); inc=XDRIncident(org,"Unified security incident",risk.explanation,risk.severity,risk.score,risk.confidence,signals=[s.id for s in group]); story=self.story.generate(org,inc.id,group,risk.confidence); inc.story=story.public(); self.repository.add_incident(inc); self.repository.stories.append(story); incidents.append(inc)
  return incidents
