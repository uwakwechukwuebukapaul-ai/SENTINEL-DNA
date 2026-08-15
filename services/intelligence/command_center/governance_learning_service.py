from .governance_learning import GovernanceLearning
from .governance_signal import stable_governance_signal_id
class GovernanceLearningService:
    def __init__(self,effectiveness=None,outcomes=None): self.effectiveness=effectiveness; self.outcomes=outcomes
    def derive(self,t):
        e=(self.effectiveness.derive(t) if self.effectiveness else {}).get('effectiveness',{}); o=(self.outcomes.derive(t) if self.outcomes else {}).get('outcomes',{}); patterns=tuple(sorted(set(e.get('effectiveness_indicators',())))); x=GovernanceLearning(t,stable_governance_signal_id(t,'governance-learning'),patterns,('Increase observed evidence before interpreting response effectiveness.',) if not patterns else (),e.get('evidence_strength','insufficient_evidence'),e.get('confidence'),tuple(sorted(set(e.get('uncertainty',()))|set(o.get('uncertainty',())))),tuple(sorted(set(e.get('provenance',()))|set(o.get('provenance',())))),True); return {'tenant_id':t,'learning':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['learning']; return x if x['learning_id']==s else None
