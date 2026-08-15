from .intervention_governance import InterventionGovernance
from .governance_signal import stable_governance_signal_id
class InterventionGovernanceService:
    def __init__(self,intervention=None,priority=None): self.intervention=intervention; self.priority=priority
    def derive(self,t):
        i=(self.intervention.derive(t) if self.intervention else {}).get('intervention',{}); p=(self.priority.derive(t) if self.priority else {}).get('priority',{}); blockers=tuple(i.get('governance_blockers',()))+tuple(i.get('readiness_blockers',())); posture='insufficient_history' if i.get('intervention_posture')=='insufficient_history' else 'blocked' if blockers else 'review' if i.get('intervention_posture')!='no_intervention_signal' else 'governed'; g=InterventionGovernance(t,stable_governance_signal_id(t,'intervention-governance'),posture,i.get('consideration_level','informational'),'insufficient_evidence' if i.get('evidence_gaps') else 'available',i.get('confidence'),tuple(i.get('uncertainty',())),tuple(i.get('provenance',())),blockers,tuple(i.get('intervention_considerations',())),('Human executive review is required before reliance.',),('Review evidence and uncertainty; no intervention is executed.',)); return {'tenant_id':t,'governance':g.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['governance']; return x if x['governance_id']==s else None
