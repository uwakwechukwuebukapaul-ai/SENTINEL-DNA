from .governance_learning_trends import GovernanceLearningTrends
from .governance_signal import stable_governance_signal_id
class GovernanceLearningTrendsService:
    def __init__(self,learning=None,effectiveness=None): self.learning=learning; self.effectiveness=effectiveness
    def derive(self,t):
        l=(self.learning.derive(t) if self.learning else {}).get('learning',{}); e=(self.effectiveness.derive(t) if self.effectiveness else {}).get('effectiveness',{}); x=GovernanceLearningTrends(t,stable_governance_signal_id(t,'governance-learning-trends'),'insufficient_history',tuple(l.get('recurring_patterns',())),tuple(l.get('lessons_learned',())),'insufficient_outcomes',l.get('evidence_strength','insufficient_evidence'),tuple(l.get('uncertainty',())),tuple(l.get('provenance',())),True); return {'tenant_id':t,'trends':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['trends']; return x if x['trends_id']==s else None
