from services.intelligence.command_center.governance_optimization_analytics_service import GovernanceOptimizationAnalyticsService
from services.intelligence.command_center.improvement_maturity_analytics_service import ImprovementMaturityAnalyticsService
from services.intelligence.command_center.strategic_evolution_command_center_service import StrategicEvolutionCommandCenterService
from services.intelligence.command_center.strategic_evolution_trends_service import StrategicEvolutionTrendsService


def test_phase3552_missing_dependencies_are_safe():
    assert StrategicEvolutionCommandCenterService(None, None, None, None).derive("tenant")["command_center"]["posture"] == "insufficient_history"
    assert GovernanceOptimizationAnalyticsService(None, None, None).derive("tenant")["analytics"]["optimization_readiness"] == "insufficient_evidence"
    assert ImprovementMaturityAnalyticsService(None, None, None).derive("tenant")["analytics"]["longitudinal_trend"] == "insufficient_history"
    assert StrategicEvolutionTrendsService(None, None, None).derive("tenant")["trends"]["evolution_trend"] == "insufficient_history"


def test_phase3552_ids_are_deterministic_and_tenant_scoped():
    first = StrategicEvolutionCommandCenterService(None, None, None, None).derive("a")["command_center"]["command_center_id"]
    assert first == StrategicEvolutionCommandCenterService(None, None, None, None).derive("a")["command_center"]["command_center_id"]
    assert first != StrategicEvolutionCommandCenterService(None, None, None, None).derive("b")["command_center"]["command_center_id"]


def test_phase3552_is_advisory_and_noncausal():
    evolution = StrategicEvolutionCommandCenterService(None, None, None, None).derive("tenant")["command_center"]
    assert evolution["advisory_only"] is True
    maturity = ImprovementMaturityAnalyticsService(None, None, None).derive("tenant")["analytics"]
    assert "causal" in maturity["progression_interpretation"]
