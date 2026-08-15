from services.intelligence.command_center.governance_learning_trends_service import GovernanceLearningTrendsService
def test_learning_trends_preserve_history_limits(): assert GovernanceLearningTrendsService().derive('a')['trends']['learning_maturity_trend']=='insufficient_history'
