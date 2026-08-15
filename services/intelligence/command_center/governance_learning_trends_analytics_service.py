from .governance_learning_trends_analytics import GovernanceLearningTrendsAnalytics
from .governance_signal import stable_governance_signal_id
class GovernanceLearningTrendsAnalyticsService:
    def __init__(self,trends=None,learning=None): self.trends=trends; self.learning=learning
    def derive(self,t):
        x=(self.trends.derive(t) if self.trends else {}).get('trends',{}); l=(self.learning.derive(t) if self.learning else {}).get('learning',{}); a=GovernanceLearningTrendsAnalytics(t,stable_governance_signal_id(t,'governance-learning-trends-analytics'),x.get('learning_maturity_trend','insufficient_history'),x.get('learning_maturity_trend','insufficient_history'),tuple(x.get('recurring_themes',())),tuple(x.get('intervention_lessons',())),x.get('evidence_maturity_trend','insufficient_evidence'),l.get('confidence'),tuple(sorted(set(x.get('uncertainty',()))|set(l.get('uncertainty',())))),tuple(sorted(set(x.get('provenance',()))|set(l.get('provenance',())))),True); return {'tenant_id':t,'analytics':a.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['analytics']; return x if x['analytics_id']==s else None
