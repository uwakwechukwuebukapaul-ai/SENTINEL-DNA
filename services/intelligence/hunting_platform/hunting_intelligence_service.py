from .ids import stable_id
from .models import HuntingIntelligence
class HuntingIntelligenceService:
 def __init__(self,repository=None,data_quality=None):self.repository,self.data_quality=repository,data_quality
 def derive(self,t):
  history=self.repository.history() if self.repository and hasattr(self.repository,'history') else ();q=self.data_quality.report(t) if self.data_quality else None
  v=HuntingIntelligence(t,stable_id(t,'hunting-intelligence'),'available' if history else 'insufficient_history','available' if history else 'insufficient_data',getattr(q,'normalization_confidence','insufficient_data') if q else 'insufficient_data','review_ready' if history else 'insufficient_history',(),('hunt history is empty',) if not history else (),getattr(q,'provenance',()) if q else (),True)
  return {'tenant_id':t,'intelligence':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['intelligence'];return v if v['intelligence_id']==i else None
