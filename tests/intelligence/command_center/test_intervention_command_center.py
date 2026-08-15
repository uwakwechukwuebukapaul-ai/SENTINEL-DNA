from services.intelligence.command_center.intervention_command_center import InterventionCommandCenter
from services.intelligence.command_center.intervention_command_center_service import InterventionCommandCenterService
def test_command_center_is_deterministic_and_immutable():
    s=InterventionCommandCenterService(); assert s.derive('a')==s.derive('a'); assert InterventionCommandCenter.__dataclass_params__.frozen
