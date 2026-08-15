from services.intelligence.command_center.intervention_governance_trends_service import InterventionGovernanceTrendsService
def test_trends_do_not_fabricate_history(): assert InterventionGovernanceTrendsService().derive('a')['trends']['governance_posture_trend']=='insufficient_history'
