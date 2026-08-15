from services.intelligence.command_center.governance_learning_command_center_service import GovernanceLearningCommandCenterService
def test_learning_command_center_is_deterministic():
    s=GovernanceLearningCommandCenterService(); assert s.derive('a')==s.derive('a'); assert s.derive('a')['advisory_only']
