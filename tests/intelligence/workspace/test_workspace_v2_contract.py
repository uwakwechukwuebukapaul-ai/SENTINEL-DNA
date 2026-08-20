import json

import pytest

from services.intelligence.workspace.v2 import AnalystWorkspaceV2Builder


def _report():
    return {
        "case_id": "CASE-WV2-1",
        "status": "completed",
        "tenant_context": {"tenant_id": "tenant-a"},
        "risk": {"score": 85, "severity": "high", "reasons": ["Endpoint evidence matched execution telemetry."]},
        "evidence": [{"evidence_id": "E-1", "tenant_id": "tenant-a", "source": "edr", "type": "process"}],
        "mitre": ["T1059.001"],
    }


def _decision():
    return {
        "verdict": "malicious",
        "confidence": 91,
        "risk_score": 85,
        "rationale": "Evidence supports a malicious execution finding.",
        "tenant_id": "tenant-a",
        "provenance": {"engine": "decision_intelligence"},
        "missing_evidence": [{"reason": "parent_process_unavailable"}],
    }


def _sequence():
    return {
        "tenant_id": "tenant-a",
        "events": [{"event_id": "EV-1", "timestamp": "2026-04-01T10:00:00Z", "stage": "execution", "description": "PowerShell execution", "evidence_references": ["E-1"], "ioc_references": ["IOC-1"], "mitre_techniques": ["T1059.001"], "confidence": 90, "provenance": {"source": "edr"}}],
        "mitre_summary": [{"technique_id": "T1059.001", "evidence_references": ["E-1"]}],
        "missing_evidence": [{"event_id": "EV-1", "reason": "command_line_unavailable"}],
        "provenance": {"analyzer": "attack_sequence_analyzer"},
    }


def test_workspace_v2_projects_evidence_backed_analyst_data_deterministically():
    builder = AnalystWorkspaceV2Builder()
    first = builder.build(_report(), decision_intelligence=_decision(), attack_sequence=_sequence(), tenant_id="tenant-a")
    second = builder.build(_report(), decision_intelligence=_decision(), attack_sequence=_sequence(), tenant_id="tenant-a")

    assert first.to_dict() == second.to_dict()
    payload = first.to_dict()
    assert payload["verdict_summary"]["verdict"] == "malicious"
    assert payload["confidence_visualization"] == {"score": 91.0, "scale": "0-100", "source": "decision_intelligence"}
    assert payload["risk_explanation"]["reasons"] == ["Endpoint evidence matched execution telemetry."]
    assert payload["evidence_references"] == [{"reference_id": "E-1", "source": "edr", "type": "process", "metadata": {}}]
    assert payload["attack_sequence_timeline"][0]["evidence_references"] == ["E-1"]
    assert payload["mitre_mappings"] == [{"technique_id": "T1059.001", "evidence_references": ["E-1"]}]
    assert {item["reason"] for item in payload["missing_evidence"]} == {"command_line_unavailable", "parent_process_unavailable"}
    assert payload["analyst_feedback"]["placeholder"]["status"] == "ready_for_analyst_feedback"
    json.dumps(payload)


def test_workspace_v2_does_not_promote_unreferenced_events_as_evidence():
    sequence = _sequence()
    sequence["events"][0]["evidence_references"] = ["E-not-present"]
    workspace = AnalystWorkspaceV2Builder().build(_report(), decision_intelligence=_decision(), attack_sequence=sequence, tenant_id="tenant-a")

    assert workspace.to_dict()["attack_sequence_timeline"] == []


def test_workspace_v2_enforces_owner_and_component_tenant_isolation():
    builder = AnalystWorkspaceV2Builder()

    with pytest.raises(PermissionError):
        builder.build(_report(), decision_intelligence=_decision(), attack_sequence=_sequence(), tenant_id="tenant-b")

    foreign = _sequence() | {"tenant_id": "tenant-b"}
    with pytest.raises(PermissionError):
        builder.build(_report(), decision_intelligence=_decision(), attack_sequence=foreign, tenant_id="tenant-a")
