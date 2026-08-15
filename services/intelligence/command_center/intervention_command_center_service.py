from .intervention_command_center import InterventionCommandCenter
from .governance_signal import stable_governance_signal_id
class InterventionCommandCenterService:
    def __init__(self,governance=None,readiness=None,lifecycle=None,planning=None): self.governance=governance; self.readiness=readiness; self.lifecycle=lifecycle; self.planning=planning
    def derive(self,t):
        g=(self.governance.derive(t) if self.governance else {}).get('governance',{}); r=(self.readiness.derive(t) if self.readiness else {}).get('readiness',{}); l=(self.lifecycle.derive(t) if self.lifecycle else {}).get('lifecycle',{}); p=(self.planning.derive(t) if self.planning else {}).get('planning',{}); x=InterventionCommandCenter(t,stable_governance_signal_id(t,'intervention-command-center'),g.get('governance_posture','insufficient_history'),r.get('readiness_classification','insufficient_history'),l.get('lifecycle_state','insufficient_history'),p.get('response_priority','P4_INFORMATIONAL'),tuple(g.get('governance_blockers',())),tuple(g.get('advisory_recommendations',())),g.get('evidence_sufficiency'),g.get('confidence'),tuple(g.get('uncertainty',())),tuple(g.get('provenance',())),True); return {'tenant_id':t,'command_center':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['command_center']; return x if x['command_center_id']==s else None
