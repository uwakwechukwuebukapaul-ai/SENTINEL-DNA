import json

from services.intelligence.investigation.attack_sequence import AttackSequenceAnalyzer
from services.intelligence.investigation.decision import DecisionIntelligenceEngine
from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator
from services.intelligence.workspace.v2 import AnalystWorkspaceV2Builder


def test_workspace_v2_projects_existing_phase18_intelligence_without_mutating_it():
    result = InvestigationResult(
        case_id="CASE-WV2-INTEGRATION",
        tenant_context={"tenant_id": "tenant-a"},
        artifacts=[{"evidence_id": "E-1", "tenant_id": "tenant-a", "source": "endpoint", "type": "process", "value": "PowerShell execution"}],
        mitre=["T1059.001"],
        risk={"score": 80, "severity": "high", "reasons": ["Observed endpoint activity"]},
    )
    result.decision_intelligence = DecisionIntelligenceEngine().evaluate(result, tenant_id="tenant-a")
    result.attack_sequence = AttackSequenceAnalyzer().analyze(
        result,
        tenant_id="tenant-a",
        timeline=[{"event_id": "EV-1", "timestamp": "2026-04-02T08:00:00Z", "description": "PowerShell execution", "evidence_references": ["E-1"], "mitre_techniques": ["T1059.001"]}],
        evidence=result.artifacts,
    )
    report = InvestigationReportGenerator().generate_from_result(result)

    workspace = AnalystWorkspaceV2Builder().build(report, result=result, tenant_id="tenant-a")
    payload = workspace.to_dict()

    assert payload["investigation"]["case_id"] == "CASE-WV2-INTEGRATION"
    assert payload["attack_sequence_timeline"][0]["event_id"] == "EV-1"
    assert payload["mitre_mappings"] == [{"technique_id": "T1059.001", "evidence_references": ["E-1"]}]
    assert result.to_dict()["attack_sequence"]["events"][0]["event_id"] == "EV-1"
    json.dumps(payload)
