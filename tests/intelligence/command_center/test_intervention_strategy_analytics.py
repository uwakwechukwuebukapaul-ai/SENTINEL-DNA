from services.intelligence.command_center.intervention_strategy_analytics_service import InterventionStrategyAnalyticsService
def test_strategy_analytics_is_advisory(): assert InterventionStrategyAnalyticsService().derive('a')['analytics']['strategy_posture']=='insufficient_evidence'
