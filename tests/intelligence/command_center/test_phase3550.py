from dataclasses import FrozenInstanceError

from services.intelligence.command_center.continuous_improvement_service import ContinuousImprovementService
from services.intelligence.command_center.governance_signal import stable_governance_signal_id
from services.intelligence.command_center.improvement_governance_service import ImprovementGovernanceService
from services.intelligence.command_center.improvement_trends_service import ImprovementTrendsService
from services.intelligence.command_center.outcome_learning_service import OutcomeLearningService


def test_phase3550_missing_dependencies_are_safe_and_deterministic():
    assert ImprovementGovernanceService(None, None).derive("t")["governance"]["portfolio_posture"] == "insufficient_history"
    assert OutcomeLearningService(None, None, None).derive("t")["outcome_learning"]["outcome_status"] == "insufficient_outcomes"
    assert ContinuousImprovementService(None, None, None).derive("t")["continuous_improvement"]["readiness"] == "insufficient_evidence"
    assert ImprovementTrendsService(None, None, None).derive("t")["trends"]["improvement_trend"] == "insufficient_history"


def test_phase3550_ids_are_tenant_scoped_and_stable():
    one = ImprovementGovernanceService(None, None).derive("one")["governance"]["governance_id"]
    assert one == ImprovementGovernanceService(None, None).derive("one")["governance"]["governance_id"]
    assert one != ImprovementGovernanceService(None, None).derive("two")["governance"]["governance_id"]


def test_phase3550_models_are_advisory_and_noncausal():
    outcome = OutcomeLearningService(None, None, None).derive("t")["outcome_learning"]
    assert outcome["advisory_only"] is True
    assert ImprovementTrendsService(None, None, None).derive("t")["trends"]["advisory_only"] is True
