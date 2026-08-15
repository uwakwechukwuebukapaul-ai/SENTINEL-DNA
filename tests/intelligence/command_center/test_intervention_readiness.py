from services.intelligence.command_center.intervention_readiness_service import InterventionReadinessService
def test_readiness_preserves_insufficient_history(): assert InterventionReadinessService().derive('a')['readiness']['readiness_classification']=='insufficient_history'
