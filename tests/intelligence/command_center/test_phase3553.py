from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.command_center.executive_strategic_intelligence_command_center_service import ExecutiveStrategicIntelligenceCommandCenterService
from services.intelligence.command_center.organizational_decision_intelligence_service import OrganizationalDecisionIntelligenceService
from services.intelligence.command_center.strategic_intelligence_health_service import StrategicIntelligenceHealthService
from services.intelligence.command_center.executive_intelligence_summary_service import ExecutiveIntelligenceSummaryService
from services.intelligence.command_center.strategic_intelligence_health import StrategicIntelligenceHealth

def test_phase3553_empty_composition_is_explicit_and_deterministic():
    services = [ExecutiveStrategicIntelligenceCommandCenterService(None,None,None,None,None,None,None,None), OrganizationalDecisionIntelligenceService(None,None,None,None), StrategicIntelligenceHealthService(), ExecutiveIntelligenceSummaryService(None,None,None)]
    keys = ["command_center", "profile", "health", "summary"]
    for service, key in zip(services, keys):
        a = service.derive("tenant")[key]
        b = service.derive("tenant")[key]
        assert a[key.replace("command_center", "command_center").replace("profile", "profile").replace("health", "health").replace("summary", "summary") + "_id"] == b[key + "_id"]
        assert a["advisory_only"] is True
    model = StrategicIntelligenceHealth("t", "h")
    with pytest.raises(FrozenInstanceError): model.coverage_posture = "covered"

def test_phase3553_insufficient_history_and_noncausal_summary():
    health = StrategicIntelligenceHealthService().derive("t")["health"]
    assert health["coverage_posture"] == "insufficient_history"
    summary = ExecutiveIntelligenceSummaryService(None,None,None).derive("t")["summary"]
    assert "Insufficient history" in summary["executive_summary"]
    assert summary["advisory_only"] is True
    assert "causal" not in summary["executive_summary"]
