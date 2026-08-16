import hashlib
from .detection_intelligence import DetectionIntelligence
def sid(t,k):return f'{k}-{hashlib.sha256(f"{t}:{k}".encode()).hexdigest()[:20]}'
class DetectionIntelligenceService:
 def __init__(self,detection=None,data_quality=None):self.detection,self.data_quality=detection,data_quality
 def derive(self,t):
  rules=self.detection.list(t) if self.detection and hasattr(self.detection,'list') else (); quality=self.data_quality.report(t) if self.data_quality and hasattr(self.data_quality,'report') else None
  v=DetectionIntelligence(t,sid(t,'detection-intelligence'),'available' if rules else 'insufficient_data',len(rules),'developing' if rules else 'insufficient_data',getattr(quality,'normalization_confidence','insufficient_data'),(),getattr(quality,'uncertainty',()) if quality else ('detection history is empty',),getattr(quality,'provenance',()) if quality else (),True)
  return {'tenant_id':t,'intelligence':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['intelligence'];return v if v['intelligence_id']==i else None
