from .detection_intelligence_service import sid
from .detection_quality import DetectionQuality
class DetectionQualityService:
 def __init__(self,validator=None,detection=None,data_quality=None):self.validator,self.detection,self.data_quality=validator,detection,data_quality
 def derive(self,t):
  rules=self.detection.list(t) if self.detection and hasattr(self.detection,'list') else ();q=self.data_quality.report(t) if self.data_quality and hasattr(self.data_quality,'report') else None
  v=DetectionQuality(t,sid(t,'detection-quality'),(('rule_count',len(rules)),) if rules else (), 'available' if rules else 'insufficient_data','available' if rules else 'insufficient_data',getattr(q,'normalization_confidence','insufficient_data') if q else 'insufficient_data',(),('rule history is empty',) if not rules else (),getattr(q,'provenance',()) if q else (),True)
  return {'tenant_id':t,'quality':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['quality'];return v if v['quality_id']==i else None
