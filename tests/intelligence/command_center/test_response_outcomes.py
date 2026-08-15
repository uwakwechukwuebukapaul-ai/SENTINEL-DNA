from services.intelligence.command_center.response_outcomes_service import ResponseOutcomesService
def test_response_outcomes_preserve_unknown_state(): assert ResponseOutcomesService().derive('a')['outcomes']['outcome_state']=='unknown'
