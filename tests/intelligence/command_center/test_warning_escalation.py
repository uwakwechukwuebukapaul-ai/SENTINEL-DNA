from services.intelligence.command_center.warning_escalation import WarningEscalation
from services.intelligence.command_center.warning_escalation_service import WarningEscalationService
class W:
    def derive(self,t): return {'early_warning':{'signals':({'signal_id':'s','category':'risk','severity':'high'},)}}
def test_escalation_is_not_operational_action():
    x=WarningEscalationService(W()).derive('a'); assert x['escalations'][0]['advisory_only']; assert WarningEscalation.__dataclass_params__.frozen
