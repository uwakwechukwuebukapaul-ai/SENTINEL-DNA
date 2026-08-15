from .escalation_lifecycle import EscalationLifecycle
from .governance_signal import stable_governance_signal_id
class EscalationLifecycleService:
    def __init__(self,escalation=None): self.escalation=escalation
    def derive(self,t):
        e=(self.escalation.derive(t) if self.escalation else {}).get('escalations',()); state='insufficient_history' if not e else 'active'; x=EscalationLifecycle(t,stable_governance_signal_id(t,'lifecycle'),state,None,'No historical transition is available.' if not e else 'Current analytical warning evidence is active.', 'unavailable' if not e else 'stable','insufficient_history' if not e else 'active',None,None,('insufficient_history',) if not e else (),(),True); return {'tenant_id':t,'lifecycle':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['lifecycle']; return x if x['lifecycle_id']==s else None
