from .governance_signal import stable_governance_signal_id
from .governance_intelligence_monitoring import GovernanceIntelligenceMonitoring
class GovernanceIntelligenceMonitoringService:
 def __init__(self,*sources):self.sources=sources
 def derive(self,t):
  vals=[s.derive(t) if s else {} for s in self.sources];p=[next((v[k] for k in ('foundation','governance','analytics','platform') if isinstance(v.get(k),dict)),v) for v in vals]
  v=GovernanceIntelligenceMonitoring(t,stable_governance_signal_id(t,'governance-intelligence-monitoring'),p[0].get('governance_workflow_intelligence','insufficient_history'),p[0].get('governance_readiness_trends','insufficient_history'),p[0].get('policy_alignment_observation','insufficient_evidence'),('human_review_required','no_policy_enforcement'),p[0].get('governance_intelligence_maturity','insufficient_history'),tuple(sorted({u for q in p for u in (q.get('uncertainty',()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get('provenance',()) or ())})),True)
  return {'tenant_id':t,'monitoring':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['monitoring'];return v if v['monitoring_id']==i else None
