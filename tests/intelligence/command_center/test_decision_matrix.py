import pytest
from services.intelligence.command_center.strategic_scenario_service import StrategicScenarioService
from services.intelligence.command_center.decision_matrix_service import DecisionMatrixService

class Strategy:
    def derive(self, tenant): return {"tenant_id":tenant,"posture":{"posture":"stable","maturity_score":60,"maturity_trajectory":"stable","confidence":.8,"evidence_strength":"strong","uncertainty":[]},"strategic_signals":[{"organizational_dimension":"investigation_quality","contributing_references":[]}]}

def service(): return DecisionMatrixService(StrategicScenarioService(Strategy()))
def selections(n=2): return [{"scenario_type":"maturity_improvement","target_dimension":"investigation_quality"},{"scenario_type":"quality_improvement","target_dimension":"investigation_quality"}][:n]
def test_matrix_is_deterministic_ranked_and_advisory():
    x=service().evaluate("a",selections()); assert x==service().evaluate("a",selections()); assert x["ranked_scenarios"]; assert x["advisory_only"] is True; assert x["trade_off_summary"]["comparability"]=="directly_comparable"
def test_matrix_limits_and_duplicates():
    with pytest.raises(ValueError): service().evaluate("a",[])
    with pytest.raises(ValueError): service().evaluate("a",selections(2)+[{"scenario_type":"quality_improvement","target_dimension":"investigation_quality"}])
    with pytest.raises(ValueError): service().evaluate("a",selections()+[{"scenario_type":"regression_reduction","target_dimension":"investigation_quality"}]*4)
