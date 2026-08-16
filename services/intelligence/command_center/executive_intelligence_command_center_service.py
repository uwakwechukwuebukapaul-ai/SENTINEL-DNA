from .governance_signal import stable_governance_signal_id
from .executive_intelligence_command_center import ExecutiveIntelligenceCommandCenter
class ExecutiveIntelligenceCommandCenterService:
 def __init__(self,*sources):self.sources=sources
 def derive(self,t):
  vals=[s.derive(t) if s else {} for s in self.sources];p=[next((v[k] for k in ('operating_system','foundation','operating_model','analytics') if isinstance(v.get(k),dict)),v) for v in vals]
  v=ExecutiveIntelligenceCommandCenter(t,stable_governance_signal_id(t,'executive-intelligence-command-center'),p[0].get('unified_operating_posture',p[0].get('operating_model_maturity','insufficient_history')),p[0].get('intelligence_capability_health','insufficient_evidence'),p[0].get('operating_model_status','insufficient_history'),p[1].get('governance_workflow_intelligence',p[1].get('automation_readiness','insufficient_evidence')),p[2].get('decision_intelligence_readiness','insufficient_history'),'Cross-domain readiness indicates advisory consideration based on available evidence; it does not make decisions.',tuple(x for q in p for x in (q.get('evidence_references',()) or ())),p[0].get('confidence'),tuple(sorted({u for q in p for u in (q.get('uncertainty',()) or ())})),tuple(sorted({str(x) for q in p for x in (q.get('provenance',()) or ())})),True)
  return {'tenant_id':t,'command_center':v.to_dict(),'advisory_only':True}
 def detail(self,t,i):
  v=self.derive(t)['command_center'];return v if v['command_center_id']==i else None
