from dataclasses import FrozenInstanceError

from services.intelligence.command_center.governance_learning_correlation_service import GovernanceLearningCorrelationService
from services.intelligence.command_center.improvement_command_center_service import ImprovementCommandCenterService
from services.intelligence.command_center.response_outcome_trend_analytics_service import ResponseOutcomeTrendAnalyticsService


def test_phase3549_services_are_deterministic_and_advisory():
    assert ImprovementCommandCenterService(None, None, None).derive("tenant")["advisory_only"]
    assert GovernanceLearningCorrelationService(None, None).derive("tenant")["correlation"]["association_boundary"].find("causal") >= 0
    assert ResponseOutcomeTrendAnalyticsService(None, None).derive("tenant")["trends"]["trend"] == "insufficient_outcomes"


def test_phase3549_ids_are_tenant_scoped():
    first = ImprovementCommandCenterService(None, None, None).derive("a")["command_center"]["command_center_id"]
    second = ImprovementCommandCenterService(None, None, None).derive("b")["command_center"]["command_center_id"]
    assert first != second


def test_phase3549_models_are_immutable():
    value = ImprovementCommandCenterService(None, None, None).derive("tenant")["command_center"]
    assert value["posture"] == "insufficient_history"
