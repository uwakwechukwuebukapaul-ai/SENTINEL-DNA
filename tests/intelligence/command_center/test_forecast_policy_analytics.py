from services.intelligence.command_center.forecast_policy_analytics_service import ForecastPolicyAnalyticsService
class P:
    def derive(self,t): return {'policy_review':{'review_id':'r','policy_readiness':'review_with_caution','uncertainty':('limited_history',),'provenance':('governance',),'confidence':'medium','evidence_strength':'moderate'},'governance':{'provenance':('governance',)}}
def test_policy_analytics_deterministic_and_advisory():
    a=ForecastPolicyAnalyticsService(P()).derive('a'); assert a==ForecastPolicyAnalyticsService(P()).derive('a'); assert a['advisory_only']
