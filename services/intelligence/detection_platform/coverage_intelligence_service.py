from .detection_intelligence_service import sid
from .coverage_intelligence import CoverageIntelligence
class CoverageIntelligenceService:
 def __init__(self,coverage=None,data_quality=None):self.coverage,self.data_quality=coverage,data_quality
 def derive(self,t):
  value=self.coverage.analyze(t) if self.coverage and hasattr(self.coverage,'analyze') else {}; q=self.data_quality.report(t) if self.data_quality and hasattr(self.data_quality,'report') else None
  v=CoverageIntelligence(t,sid(t,'coverage-intelligence'),value.get('posture','insufficient_data'),'available' if q and q.observed_event_count else 'insufficient_data',tuple(value.get('indicators',())),tuple(value.get('blind_spots',())),value.get('confidence','insufficient_data'),tuple(getattr(q,'uncertainty',())) if q else ('coverage history is empty',),tuple(getattr(q,'provenance',())) if q else (),True)
  return {'tenant_id':t,'coverage':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['coverage'];return v if v['coverage_id']==i else None
