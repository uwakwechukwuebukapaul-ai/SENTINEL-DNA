from .intervention_strategy_analytics import InterventionStrategyAnalytics
from .governance_signal import stable_governance_signal_id
class InterventionStrategyAnalyticsService:
    def __init__(self,effectiveness=None,learning=None): self.effectiveness=effectiveness; self.learning=learning
    def derive(self,t):
        e=(self.effectiveness.derive(t) if self.effectiveness else {}).get('effectiveness',{}); l=(self.learning.derive(t) if self.learning else {}).get('learning',{}); x=InterventionStrategyAnalytics(t,stable_governance_signal_id(t,'intervention-strategy-analytics'),'insufficient_evidence',(),tuple(e.get('effectiveness_indicators',())),e.get('readiness_alignment','insufficient_evidence'),'insufficient_evidence',('Potential improvement opportunity: increase observed evidence before strategy consideration.',),tuple(e.get('uncertainty',())),e.get('confidence'),tuple(sorted(set(e.get('provenance',()))|set(l.get('provenance',())))),True); return {'tenant_id':t,'analytics':x.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['analytics']; return x if x['analytics_id']==s else None
