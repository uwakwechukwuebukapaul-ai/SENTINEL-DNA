import pytest
from services.intelligence.command_center.strategic_scenario_service import StrategicScenarioService

class Strategy:
    def derive(self, tenant):
        return {"tenant_id":tenant,"posture":{"posture":"stable","maturity_score":61,"maturity_trajectory":"stable","confidence":.7,"evidence_strength":"moderate","uncertainty":[]},"strategic_signals":[{"organizational_dimension":"investigation_quality","contributing_references":["r1"]}],"advisory_only":True}

def test_scenario_is_deterministic_bounded_and_advisory():
    service=StrategicScenarioService(Strategy())
    payload={"scenario_type":"maturity_improvement","target_dimension":"investigation_quality","assumption":"Improve the identified dimension."}
    first=service.evaluate("a",payload); assert first==service.evaluate("a",payload); assert first["scenario_score"]<=100; assert first["advisory_only"] is True; assert first["score_delta"]<=20

def test_invalid_scenarios_and_tenants():
    service=StrategicScenarioService(Strategy())
    with pytest.raises(ValueError): service.evaluate("a",{"scenario_type":"unknown","assumption":"x"})
    with pytest.raises(ValueError): service.evaluate("a",{"scenario_type":"maturity_improvement","target_dimension":"missing","assumption":"x"})
    assert service.options("b")["tenant_id"]=="b"
