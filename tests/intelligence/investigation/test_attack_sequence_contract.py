import json

import pytest

from services.intelligence.investigation.attack_sequence import AttackSequenceAnalyzer


def _source_data():
    return {
        "case_id": "CASE-18-2",
        "tenant_context": {"tenant_id": "tenant-a"},
        "mitre": ["T1059.001"],
    }


def _evidence():
    return [
        {"evidence_id": "E-1", "tenant_id": "tenant-a", "source": "edr", "value": "PowerShell execution"},
        {"evidence_id": "E-2", "tenant_id": "tenant-a", "source": "identity", "value": "authentication log"},
    ]


def _iocs():
    return [{"ioc_id": "IOC-1", "tenant_id": "tenant-a", "value": "185.220.101.44"}]


def test_attack_sequence_is_deterministic_ordered_and_evidence_grounded():
    timeline = [
        {"event_id": "EV-2", "timestamp": "2026-02-01T10:05:00Z", "description": "PowerShell execution", "evidence_references": ["E-1"], "ioc_references": ["IOC-1"], "mitre_techniques": ["T1059.001"]},
        {"event_id": "EV-1", "timestamp": "2026-02-01T10:00:00Z", "description": "Authentication activity", "evidence_references": ["E-2"]},
    ]
    analyzer = AttackSequenceAnalyzer()

    first = analyzer.analyze(_source_data(), tenant_id="tenant-a", timeline=timeline, evidence=_evidence(), iocs=_iocs())
    second = analyzer.analyze(_source_data(), tenant_id="tenant-a", timeline=list(reversed(timeline)), evidence=_evidence(), iocs=_iocs())

    assert first.to_dict() == second.to_dict()
    assert [event.event_id for event in first.events] == ["EV-1", "EV-2"]
    assert first.events[1].evidence_references == ["E-1"]
    assert first.events[1].ioc_references == ["IOC-1"]
    assert first.events[1].mitre_techniques == ["T1059.001"]
    assert first.events[1].stage == "execution"
    assert all(0 <= event.confidence <= 100 for event in first.events)
    assert first.mitre_summary == [{"technique_id": "T1059.001", "evidence_references": ["E-1"]}]


def test_attack_sequence_does_not_fabricate_missing_timestamps_or_mitre():
    sequence = AttackSequenceAnalyzer().analyze(
        _source_data() | {"mitre": []},
        tenant_id="tenant-a",
        timeline=[{"event_id": "EV-no-time", "description": "PowerShell execution", "evidence_references": ["E-1"]}],
        evidence=_evidence(),
        iocs=_iocs(),
    )

    assert sequence.events == []
    assert {item["reason"] for item in sequence.missing_evidence} >= {"timeline_timestamp_missing"}
    assert sequence.mitre_summary == []
    assert "No evidence-backed attack sequence" in sequence.attack_story


def test_attack_sequence_enforces_tenant_isolation_and_json_serialization():
    timeline = [{"event_id": "EV-1", "timestamp": "2026-02-01T10:00:00Z", "description": "Observed event", "evidence_references": ["E-1"]}]
    analyzer = AttackSequenceAnalyzer()

    with pytest.raises(PermissionError):
        analyzer.analyze(_source_data(), tenant_id="tenant-b", timeline=timeline, evidence=_evidence())

    sequence = analyzer.analyze(_source_data(), tenant_id="tenant-a", timeline=timeline, evidence=_evidence())
    assert sequence.tenant_id == "tenant-a"
    json.dumps(sequence.to_dict())
