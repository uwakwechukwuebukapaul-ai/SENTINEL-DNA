from .escalation_monitoring import EscalationMonitoring
from .governance_signal import stable_governance_signal_id
class EscalationMonitoringService:
    def __init__(self,lifecycle=None): self.lifecycle=lifecycle
    def derive(self,t):
        l=(self.lifecycle.derive(t) if self.lifecycle else {}).get('lifecycle',{}); state=l.get('lifecycle_state','insufficient_history'); x=EscalationMonitoring(t,stable_governance_signal_id(t,'escalation-monitoring'),{state:1},'insufficient_history' if state=='insufficient_history' else 'stable','insufficient_history',(),l.get('persistence_interpretation','insufficient_history'), 'insufficient_history' if state=='insufficient_history' else 'stable',l.get('evidence_strength'),l.get('confidence'),tuple(l.get('uncertainty',())),tuple(l.get('provenance',())),True); return {'tenant_id':t,'monitoring':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['monitoring']; return x if x['monitoring_id']==s else None
