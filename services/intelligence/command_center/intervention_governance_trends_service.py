from .intervention_governance_trends import InterventionGovernanceTrends
from .governance_signal import stable_governance_signal_id
class InterventionGovernanceTrendsService:
    def __init__(self,command_center=None): self.command_center=command_center
    def derive(self,t):
        c=(self.command_center.derive(t) if self.command_center else {}).get('command_center',{}); state='insufficient_history' if not c or c.get('governance_posture')=='insufficient_history' else 'stable'; x=InterventionGovernanceTrends(t,stable_governance_signal_id(t,'intervention-governance-trends'),state,state,state,state,'insufficient_history' if state=='insufficient_history' else 'limited',tuple(c.get('uncertainty',())),tuple(c.get('provenance',())),True); return {'tenant_id':t,'trends':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['trends']; return x if x['trends_id']==s else None
