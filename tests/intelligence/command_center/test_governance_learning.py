from services.intelligence.command_center.governance_learning_service import GovernanceLearningService
def test_learning_preserves_evidence_limits(): assert GovernanceLearningService().derive('a')['learning']['evidence_strength']=='insufficient_evidence'
