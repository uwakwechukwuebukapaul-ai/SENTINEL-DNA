from .strategic_improvement_portfolio_analytics import StrategicImprovementPortfolioAnalytics
from .governance_signal import stable_governance_signal_id
class StrategicImprovementPortfolioAnalyticsService:
    def __init__(self,portfolio=None,learning=None,strategy=None): self.portfolio=portfolio; self.learning=learning; self.strategy=strategy
    def derive(self,t):
        l=(self.learning.derive(t) if self.learning else {}).get('learning',{}); s=(self.strategy.derive(t) if self.strategy else {}).get('analytics',{}); themes=tuple(sorted(set(l.get('recurring_patterns',())))); a=StrategicImprovementPortfolioAnalytics(t,stable_governance_signal_id(t,'strategic-improvement-portfolio'),'insufficient_history' if not themes else 'learning_available',themes,tuple(s.get('strategy_patterns',())),(),(),tuple(l.get('lessons_learned',())),tuple(s.get('effectiveness_patterns',())),themes,s.get('evidence_strength'),s.get('confidence'),tuple(sorted(set(s.get('uncertainty',()))|set(l.get('uncertainty',())))),tuple(sorted(set(s.get('provenance',()))|set(l.get('provenance',())))),True); return {'tenant_id':t,'portfolio':a.to_dict(),'advisory_only':True}
    def detail(self,t,s): x=self.derive(t)['portfolio']; return x if x['portfolio_id']==s else None
