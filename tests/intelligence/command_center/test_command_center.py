from services.intelligence.command_center import CommandCenterRepository, SOCCommandCenterService
from services.intelligence.investigation.investigation_result import InvestigationResult

def rows():
    return [{"tenant_id": "a", "investigation_id": "i1", "case_id": "c1", "status": "active", "risk": {"severity": "critical"}, "evidence": [{"id": "e1"}], "mitre": ["T1059"], "threat_intelligence_report": {"threat_score": 80}, "vulnerabilities": [{}], "attack_paths": [{}]}]

def test_aggregation_correctness():
    snapshot = SOCCommandCenterService(CommandCenterRepository(rows()), tenant_id="a").get_snapshot()
    assert snapshot.executive_posture.critical_investigations == 1
    assert snapshot.threat_posture.mitre_techniques == ["T1059"]
    assert snapshot.threat_posture.threat_score == 80

def test_tenant_isolation():
    service = SOCCommandCenterService(CommandCenterRepository(rows()), tenant_id="b")
    assert service.get_snapshot().investigations == []

def test_partial_failure_handling():
    snapshot = SOCCommandCenterService(CommandCenterRepository()).get_snapshot()
    assert snapshot.availability == "partial"

def test_decisions_require_human_approval():
    row = {"tenant_id": "a", "decision_id": "d1", "decision_type": "soar_approval", "title": "Contain host"}
    decisions = SOCCommandCenterService(CommandCenterRepository(rows(), [row]), tenant_id="a").get_pending_decisions()
    assert decisions[0].requires_human_approval is True

def test_backward_compatibility():
    result = InvestigationResult()
    assert result.command_center_context is None and "command_center_context" in result.to_dict()
