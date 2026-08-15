from .governance_learning_command_center import GovernanceLearningCommandCenter
from .governance_signal import stable_governance_signal_id
class GovernanceLearningCommandCenterService:
    def __init__(self,learning=None,effectiveness=None,outcomes=None): self.learning=learning; self.effectiveness=effectiveness; self.outcomes=outcomes
    def derive(self,t):
        l=(self.learning.derive(t) if self.learning else {}).get('learning',{}); e=(self.effectiveness.derive(t) if self.effectiveness else {}).get('effectiveness',{}); o=(self.outcomes.derive(t) if self.outcomes else {}).get('outcomes',{}); x=GovernanceLearningCommandCenter(t,stable_governance_signal_id(t,'governance-learning-command-center'),'insufficient_history' if not l else 'learning_available',e.get('assessment','insufficient_history'),o.get('outcome_state','unknown'),tuple(l.get('recurring_patterns',())),tuple(e.get('effectiveness_indicators',())),tuple(l.get('lessons_learned',())),l.get('evidence_strength'),l.get('confidence'),tuple(l.get('uncertainty',())),tuple(l.get('provenance',())),tuple(l.get('lessons_learned',())),True); return {'tenant_id':t,'command_center':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['command_center']; return x if x['command_center_id']==s else None
