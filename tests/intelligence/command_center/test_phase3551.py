from services.intelligence.command_center.governance_learning_optimization_service import GovernanceLearningOptimizationService
from services.intelligence.command_center.improvement_maturity_service import ImprovementMaturityService
from services.intelligence.command_center.strategic_evolution_service import StrategicEvolutionService


def test_phase3551_missing_data_is_safe():
    assert GovernanceLearningOptimizationService(None, None, None).derive("tenant")["optimization"]["posture"] == "insufficient_evidence"
    assert StrategicEvolutionService(None, None, None).derive("tenant")["evolution"]["convergence"] == "insufficient_history"
    assert ImprovementMaturityService(None, None, None).derive("tenant")["maturity"]["posture"] == "insufficient_history"


def test_phase3551_ids_are_deterministic_and_tenant_scoped():
    first = StrategicEvolutionService(None, None, None).derive("a")["evolution"]["evolution_id"]
    assert first == StrategicEvolutionService(None, None, None).derive("a")["evolution"]["evolution_id"]
    assert first != StrategicEvolutionService(None, None, None).derive("b")["evolution"]["evolution_id"]


def test_phase3551_is_advisory_and_noncausal():
    evolution = StrategicEvolutionService(None, None, None).derive("tenant")["evolution"]
    assert evolution["advisory_only"] is True
    assert "causal" in evolution["modeled_interpretation"]
