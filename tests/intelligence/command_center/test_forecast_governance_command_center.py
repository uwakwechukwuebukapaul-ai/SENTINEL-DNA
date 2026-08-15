from services.intelligence.command_center.forecast_governance_command_center import ForecastGovernanceCommandCenter
from services.intelligence.command_center.forecast_governance_command_center_service import ForecastGovernanceCommandCenterService
class P:
    def derive(self,t): return {'analytics':{'history_status':'insufficient_history'},'governance':{},'readiness':{'x':1}}
class R:
    def derive(self,t): return {'readiness':{'readiness_classification':'insufficient_history','uncertainty':('insufficient_history',),'provenance':()}}
def test_command_center_is_immutable_and_deterministic():
    s=ForecastGovernanceCommandCenterService(P(),R()); assert s.derive('a')==s.derive('a'); assert ForecastGovernanceCommandCenter.__dataclass_params__.frozen
