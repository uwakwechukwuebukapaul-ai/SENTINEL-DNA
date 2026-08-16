from services.intelligence.command_center.operating_model_analytics_service import OperatingModelAnalyticsService
def test_operating_model_analytics_is_stable_and_noncausal():
    a=OperatingModelAnalyticsService(None,None).derive('t')['analytics']; b=OperatingModelAnalyticsService(None,None).derive('t')['analytics']; assert a['analytics_id']==b['analytics_id']; assert a['intelligence_operating_model_trends']=='insufficient_history'; assert a['advisory_only']
