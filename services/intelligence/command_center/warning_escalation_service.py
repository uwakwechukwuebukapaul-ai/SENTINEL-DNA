from .warning_escalation import WarningEscalation
from .governance_signal import stable_governance_signal_id
class WarningEscalationService:
    def __init__(self,early_warning=None): self.early_warning=early_warning
    def derive(self,t):
        w=self.early_warning.derive(t) if self.early_warning else {}; x=w.get('early_warning',{}); out=[]
        for s in sorted(x.get('signals',()),key=lambda z:z.get('signal_id','')): out.append(WarningEscalation(t,stable_governance_signal_id(t,'escalation',s.get('signal_id')),s.get('signal_id'),s.get('category','governance'),'unavailable',s.get('severity','informational'),'insufficient_history',s.get('severity','informational'),'unavailable',tuple(s.get('evidence',())),s.get('confidence'),tuple(s.get('uncertainty',())),tuple(s.get('references',())),s.get('organizational_dimension')) .to_dict())
        return {'tenant_id':t,'escalations':tuple(out),'advisory_only':True}
    def detail(self,t,i): return next((x for x in self.derive(t)['escalations'] if x['escalation_id']==i),None)
