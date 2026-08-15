from .response_monitoring import ResponseMonitoring
from .governance_signal import stable_governance_signal_id
class ResponseMonitoringService:
    def __init__(self,outcomes=None): self.outcomes=outcomes
    def derive(self,t):
        o=(self.outcomes.derive(t) if self.outcomes else {}).get('outcomes',{}); state=o.get('outcome_state','unknown'); trend='insufficient_history' if state=='unknown' else state; x=ResponseMonitoring(t,stable_governance_signal_id(t,'response-monitoring'),trend,'insufficient_history' if state=='unknown' else 'unavailable',(),(),('Response outcome evidence is unavailable.',) if state=='unknown' else (),tuple(o.get('uncertainty',())),o.get('confidence'),tuple(o.get('provenance',())),True); return {'tenant_id':t,'monitoring':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['monitoring']; return x if x['monitoring_id']==s else None
