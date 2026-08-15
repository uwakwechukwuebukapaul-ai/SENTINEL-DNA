from .response_effectiveness import ResponseEffectiveness
from .governance_signal import stable_governance_signal_id
class ResponseEffectivenessService:
    def __init__(self,planning=None,readiness=None): self.planning=planning; self.readiness=readiness
    def derive(self,t):
        p=(self.planning.derive(t) if self.planning else {}).get('planning',{}); r=(self.readiness.derive(t) if self.readiness else {}).get('readiness',{}); x=ResponseEffectiveness(t,stable_governance_signal_id(t,'response-effectiveness'),'insufficient_evidence','insufficient evidence for effectiveness assessment',('Observed progress or outcome evidence.',),(), 'insufficient_evidence',r.get('confidence'),tuple(r.get('uncertainty',())),tuple(p.get('provenance',())),True); return {'tenant_id':t,'effectiveness':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['effectiveness']; return x if x['effectiveness_id']==s else None
