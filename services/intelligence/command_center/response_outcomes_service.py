from .response_outcomes import ResponseOutcomes
from .governance_signal import stable_governance_signal_id
class ResponseOutcomesService:
    def __init__(self,effectiveness=None): self.effectiveness=effectiveness
    def derive(self,t):
        e=(self.effectiveness.derive(t) if self.effectiveness else {}).get('effectiveness',{}); x=ResponseOutcomes(t,stable_governance_signal_id(t,'response-outcomes'),'unknown',tuple(e.get('effectiveness_indicators',())), 'Observed response outcomes are unavailable; no causal conclusion is made.',e.get('evidence_strength'),e.get('confidence'),tuple(e.get('uncertainty',())),tuple(e.get('provenance',())),True); return {'tenant_id':t,'outcomes':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['outcomes']; return x if x['outcomes_id']==s else None
