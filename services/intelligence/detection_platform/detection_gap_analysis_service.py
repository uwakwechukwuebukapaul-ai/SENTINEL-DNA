from .detection_intelligence_service import sid
from .detection_gap_analysis import DetectionGapAnalysis
class DetectionGapAnalysisService:
 def __init__(self,coverage=None,data_quality=None):self.coverage,self.data_quality=coverage,data_quality
 def derive(self,t):
  value=self.coverage.analyze(t) if self.coverage and hasattr(self.coverage,'analyze') else {};q=self.data_quality.report(t) if self.data_quality and hasattr(self.data_quality,'report') else None
  v=DetectionGapAnalysis(t,sid(t,'detection-gap-analysis'),tuple(value.get('blind_spots',())) if value else (),('Review observed coverage blind spots; this is advisory consideration only.',) if value else (),('telemetry availability requires evidence',) if not q or not q.observed_event_count else (),('human analyst review required',),getattr(q,'normalization_confidence','insufficient_data') if q else 'insufficient_data',('insufficient detection history',) if not value else (),getattr(q,'provenance',()) if q else (),True)
  return {'tenant_id':t,'gaps':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['gaps'];return v if v['analysis_id']==i else None
