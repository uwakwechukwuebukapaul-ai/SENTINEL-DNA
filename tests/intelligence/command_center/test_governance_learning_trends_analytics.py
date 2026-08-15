from services.intelligence.command_center.governance_learning_trends_analytics_service import GovernanceLearningTrendsAnalyticsService
def test_trend_analytics_is_deterministic(): assert GovernanceLearningTrendsAnalyticsService().derive('a')==GovernanceLearningTrendsAnalyticsService().derive('a')
