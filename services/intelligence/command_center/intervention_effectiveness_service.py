from .intervention_effectiveness import InterventionEffectiveness
from .governance_signal import stable_governance_signal_id
class InterventionEffectivenessService:
    def __init__(self,readiness=None,effectiveness=None): self.readiness=readiness; self.effectiveness=effectiveness
    def derive(self,t):
        r=(self.readiness.derive(t) if self.readiness else {}).get('readiness',{}); e=(self.effectiveness.derive(t) if self.effectiveness else {}).get('effectiveness',{}); x=InterventionEffectiveness(t,stable_governance_signal_id(t,'intervention-effectiveness'),'insufficient_history' if not r else 'insufficient_evidence',r.get('readiness_classification','insufficient_evidence'),('readiness_observed',) if r else (), 'Observed alongside response planning; causality is not established.',e.get('evidence_strength'),r.get('confidence'),tuple(r.get('uncertainty',())),tuple(r.get('provenance',())),True); return {'tenant_id':t,'effectiveness':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['effectiveness']; return x if x['effectiveness_id']==s else None
