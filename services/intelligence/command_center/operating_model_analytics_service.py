from .governance_signal import stable_governance_signal_id
from .operating_model_analytics import OperatingModelAnalytics
class OperatingModelAnalyticsService:
 def __init__(self,*sources):self.sources=sources
 def derive(self,t):
  vals=[s.derive(t) if s else {} for s in self.sources];p=[next((v[k] for k in ('operating_model','maturity','adoption','feedback') if isinstance(v.get(k),dict)),v) for v in vals]
  v=OperatingModelAnalytics(t,stable_governance_signal_id(t,'operating-model-analytics'),p[0].get('intelligence_operating_model_trends','insufficient_history'),p[0].get('capability_maturity_progression',p[0].get('ai_maturity_level','insufficient_history')),tuple(x for q in p for x in (q.get('intelligence_adoption_signals',()) or ())),tuple(x for q in p for x in (q.get('continuous_improvement_observations',q.get('improvement_opportunities',())) or ())),p[0].get('evidence_strength','insufficient_evidence'),tuple(sorted({u for q in p for u in (q.get('uncertainty',()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get('provenance',()) or ())})),True)
  return {'tenant_id':t,'analytics':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['analytics'];return v if v['analytics_id']==i else None
