import json

from services.intelligence.investigation.attack_sequence import AttackSequenceAnalyzer
from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator


def test_attack_sequence_flows_from_result_to_analyst_report_as_plain_data():
    result = InvestigationResult(
        case_id="CASE-18-2-INTEGRATION",
        tenant_context={"tenant_id": "tenant-a"},
        artifacts=[{"evidence_id": "E-1", "tenant_id": "tenant-a", "source": "endpoint", "value": "PowerShell execution"}],
        mitre=["T1059.001"],
    )
    result.attack_sequence = AttackSequenceAnalyzer().analyze(
        result,
        tenant_id="tenant-a",
        timeline=[{"event_id": "EV-1", "timestamp": "2026-03-01T09:00:00Z", "description": "PowerShell execution", "evidence_references": ["E-1"], "mitre_techniques": ["T1059.001"]}],
        evidence=result.artifacts,
    )

    report = InvestigationReportGenerator().generate_from_result(result)
    result_payload = result.to_dict()
    report_payload = report.to_dict()

    assert result_payload["attack_sequence"]["events"][0]["event_id"] == "EV-1"
    assert report_payload["attack_sequence"] == result_payload["attack_sequence"]
    assert report_payload["attack_sequence"]["mitre_summary"] == [{"technique_id": "T1059.001", "evidence_references": ["E-1"]}]
    json.dumps(result_payload)
    json.dumps(report_payload)
