from .intervention_priority import InterventionPriority
from .governance_signal import stable_governance_signal_id
class InterventionPriorityService:
    def __init__(self,intervention=None): self.intervention=intervention
    def derive(self,t):
        x=(self.intervention.derive(t) if self.intervention else {}).get('intervention',{}); p=InterventionPriority(t,stable_governance_signal_id(t,'priority'),x.get('intervention_priority','P4_INFORMATIONAL'),tuple(x.get('intervention_rationale',())),tuple(x.get('active_warnings',())),tuple(x.get('evidence_gaps',())),tuple(x.get('intervention_considerations',())),tuple(x.get('organizational_dimensions',())),x.get('temporal_coverage','unavailable'),x.get('confidence'),tuple(x.get('uncertainty',())),tuple(x.get('provenance',())),True); return {'tenant_id':t,'priority':p.to_dict(),'advisory_only':True}
    def detail(self,t,i): x=self.derive(t)['priority']; return x if x['priority_id']==i else None
