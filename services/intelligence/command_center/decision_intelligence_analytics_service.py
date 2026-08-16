from .governance_signal import stable_governance_signal_id
from .decision_intelligence_analytics import DecisionIntelligenceAnalytics
class DecisionIntelligenceAnalyticsService:
 def __init__(self,*sources):self.sources=sources
 def derive(self,t):
  vals=[s.derive(t) if s else {} for s in self.sources];p=[next((v[k] for k in ('foundation','lifecycle','profile','health') if isinstance(v.get(k),dict)),v) for v in vals]
  v=DecisionIntelligenceAnalytics(t,stable_governance_signal_id(t,'decision-intelligence-analytics'),p[0].get('decision_intelligence_readiness','insufficient_history'),p[0].get('evidence_to_decision_traceability','insufficient_evidence'),p[0].get('decision_context_completeness','insufficient_history'),p[0].get('decision_lifecycle_visibility','insufficient_history'),p[0].get('review_readiness','insufficient_history'),tuple(sorted({u for q in p for u in (q.get('uncertainty',()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get('provenance',()) or ())})),True)
  return {'tenant_id':t,'analytics':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['analytics'];return v if v['analytics_id']==i else None
