from services.intelligence.command_center.decision_readiness_analytics_service import DecisionReadinessAnalyticsService
class R:
    def derive(self,t): return {'readiness':{'readiness_classification':'insufficient_history','uncertainty':('insufficient_history',),'provenance':()}}
def test_readiness_analytics_does_not_fabricate_history():
    x=DecisionReadinessAnalyticsService(R()).derive('a'); assert x['analytics']['history_status']=='limited_history'; assert x['analytics']['state_transitions']==()
