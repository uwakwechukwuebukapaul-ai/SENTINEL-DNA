from services.intelligence.command_center.risk_response_planning_service import RiskResponsePlanningService
def test_response_planning_is_advisory(): assert RiskResponsePlanningService().derive('a')['advisory_only']
