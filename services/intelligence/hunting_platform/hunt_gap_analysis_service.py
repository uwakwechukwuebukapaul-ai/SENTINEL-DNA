from .ids import stable_id
from .models import HuntGapAnalysis
class HuntGapAnalysisService:
 def __init__(self,intelligence=None):self.intelligence=intelligence
 def derive(self,t):
  base=self.intelligence.derive(t) if self.intelligence else {};empty=base.get('intelligence',{}).get('current_hunting_posture')=='insufficient_history';v=HuntGapAnalysis(t,stable_id(t,'hunt-gap-analysis'),('hunting coverage history',) if empty else (),('telemetry visibility requires evidence',) if empty else (),('hunting maturity history',) if empty else (),('human analyst review of observed gaps',), 'insufficient_data' if empty else 'moderate',True)
  return {'tenant_id':t,'gaps':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['gaps'];return v if v['analysis_id']==i else None
