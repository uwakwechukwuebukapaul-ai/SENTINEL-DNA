from services.intelligence.command_center.governance_posture_analytics_service import GovernancePostureAnalyticsService
class C:
    def derive(self,t): return {'command_center':{'governance_posture':'insufficient_history','uncertainty':('insufficient_history',)}}
def test_history_does_not_fabricate_transitions():
    x=GovernancePostureAnalyticsService(C()).derive('a'); assert x['history']['trajectory']=='insufficient_history'; assert x['history']['posture_transitions']==()
