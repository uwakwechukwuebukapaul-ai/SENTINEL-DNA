import json
from pathlib import Path

import pytest

from sentinel_dna.investigation import InvestigationCoordinator
from sentinel_dna.telemetry import (
    JSONTelemetryAdapter,
    SecurityAlert,
    SentinelTelemetryAdapter,
    TelemetryValidationError,
)


def sentinel_event():
    return {
        "SystemAlertId": "SENTINEL-ALT-001",
        "AlertName": "Suspicious Authentication Activity",
        "Description": (
            "Multiple suspicious authentication attempts detected "
            "against a privileged account."
        ),
        "Severity": "High",
        "TimeGenerated": "2026-08-11T20:00:00Z",
        "ProviderName": "Microsoft Defender for Cloud",
        "ProductName": "Microsoft Sentinel",
        "CompromisedEntity": "WORKSTATION-01",
        "Entities": [
            {
                "Type": "account",
                "Name": "alice@example.com",
            },
            {
                "Type": "host",
                "HostName": "WORKSTATION-01",
            },
            {
                "Type": "ip",
                "Address": "203.0.113.50",
            },
            {
                "Type": "dns",
                "DomainName": "example-login.com",
            },
            {
                "Type": "filehash",
                "Value": "0123456789abcdef",
            },
        ],
        "Tactics": ["CredentialAccess"],
        "Techniques": ["T1110"],
        "ExtendedProperties": {
            "RuleId": "AUTH-001",
            "DetectionSource": "Identity",
        },
    }


def test_sentinel_adapter_normalizes_alert():
    adapter = SentinelTelemetryAdapter()

    alert = adapter.normalize(sentinel_event())

    assert isinstance(alert, SecurityAlert)
    assert alert.alert_id == "SENTINEL-ALT-001"
    assert alert.title == "Suspicious Authentication Activity"
    assert alert.severity == "high"
    assert alert.timestamp == "2026-08-11T20:00:00Z"
    assert (
        alert.source
        == "Microsoft Defender for Cloud/Microsoft Sentinel"
    )


def test_sentinel_adapter_normalizes_entities():
    alert = SentinelTelemetryAdapter().normalize(sentinel_event())

    assert alert.entities["users"] == ["alice@example.com"]
    assert alert.entities["hosts"] == ["WORKSTATION-01"]
    assert alert.entities["ips"] == ["203.0.113.50"]
    assert alert.entities["domains"] == ["example-login.com"]
    assert alert.entities["hashes"] == ["0123456789abcdef"]


def test_sentinel_adapter_preserves_raw_event():
    event = sentinel_event()

    alert = SentinelTelemetryAdapter().normalize(event)

    assert alert.raw_event == event
    assert alert.raw_event is not event


def test_sentinel_adapter_preserves_vendor_metadata():
    alert = SentinelTelemetryAdapter().normalize(sentinel_event())

    assert alert.metadata["provider"] == "Microsoft Defender for Cloud"
    assert alert.metadata["product"] == "Microsoft Sentinel"
    assert alert.metadata["tactics"] == ["CredentialAccess"]
    assert alert.metadata["techniques"] == ["T1110"]
    assert alert.metadata["compromised_entity"] == "WORKSTATION-01"
    assert alert.metadata["extended_properties"]["RuleId"] == "AUTH-001"


def test_sentinel_adapter_converts_to_investigation_alert():
    alert = SentinelTelemetryAdapter().normalize(sentinel_event())

    investigation_alert = alert.to_investigation_alert()

    assert investigation_alert["alert_id"] == "SENTINEL-ALT-001"
    assert investigation_alert["title"] == (
        "Suspicious Authentication Activity"
    )
    assert investigation_alert["subject"] == (
        "Suspicious Authentication Activity"
    )
    assert investigation_alert["severity"] == "high"
    assert investigation_alert["entities"]["users"] == [
        "alice@example.com"
    ]
    assert "alice@example.com" in investigation_alert["body"]
    assert investigation_alert["raw_event"] == alert.raw_event


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("Informational", "informational"),
        ("Information", "informational"),
        ("Info", "informational"),
        ("Low", "low"),
        ("Medium", "medium"),
        ("Moderate", "medium"),
        ("High", "high"),
        ("Critical", "critical"),
        ("Severe", "critical"),
    ],
)
def test_sentinel_adapter_normalizes_severity(severity, expected):
    event = sentinel_event()
    event["Severity"] = severity

    alert = SentinelTelemetryAdapter().normalize(event)

    assert alert.severity == expected


def test_sentinel_adapter_requires_alert_id():
    event = sentinel_event()
    event.pop("SystemAlertId")

    with pytest.raises(
        TelemetryValidationError,
        match="missing required alert ID",
    ):
        SentinelTelemetryAdapter().normalize(event)


def test_sentinel_adapter_requires_title():
    event = sentinel_event()
    event.pop("AlertName")

    with pytest.raises(
        TelemetryValidationError,
        match="missing required title",
    ):
        SentinelTelemetryAdapter().normalize(event)


def test_sentinel_adapter_rejects_invalid_event():
    with pytest.raises(
        TelemetryValidationError,
        match="raw_event must be a dictionary or mapping",
    ):
        SentinelTelemetryAdapter().normalize(
            "not-a-sentinel-event"
        )


def test_sentinel_adapter_accepts_mapping_style_entities():
    event = sentinel_event()

    event["Entities"] = {
        "users": ["alice@example.com"],
        "hosts": ["WORKSTATION-01"],
        "ips": ["203.0.113.50"],
        "domains": ["example-login.com"],
        "hashes": ["0123456789abcdef"],
    }

    alert = SentinelTelemetryAdapter().normalize(event)

    assert alert.entities == {
        "users": ["alice@example.com"],
        "hosts": ["WORKSTATION-01"],
        "ips": ["203.0.113.50"],
        "domains": ["example-login.com"],
        "hashes": ["0123456789abcdef"],
    }


def test_sentinel_adapter_integrates_with_investigator(tmp_path):
    raw_event = sentinel_event()

    alert = SentinelTelemetryAdapter().normalize(raw_event)
    investigation_alert = alert.to_investigation_alert()

    result = InvestigationCoordinator(Path(tmp_path)).investigate(
        "sentinel-v2-001",
        investigation_alert,
    )

    assert result.plan_name == "ai-investigator-v1"
    assert result.errors == []
    assert result.results["case_id"] == "sentinel-v2-001"
    assert len(result.results["tasks"]) == 17
    assert result.results["evidence"]
    assert result.results["risk"]["score"] > 0

    serialized = result.to_dict()

    assert set(serialized) == {
        "plan_name",
        "results",
        "errors",
    }

    json.dumps(serialized)


def test_existing_json_adapter_contract_remains_compatible():
    raw_event = {
        "id": "JSON-001",
        "source": "demo-soc",
        "timestamp": "2026-08-11T20:00:00Z",
        "title": "Suspicious Authentication Activity",
        "severity": "HIGH",
        "description": "Suspicious authentication detected.",
        "entities": {
            "users": ["alice@example.com"],
            "hosts": ["WORKSTATION-01"],
            "ips": ["203.0.113.50"],
            "domains": ["example-login.com"],
            "hashes": [],
        },
        "metadata": {
            "rule": "AUTH-001",
        },
    }

    alert = JSONTelemetryAdapter().normalize(raw_event)

    assert alert.alert_id == "JSON-001"
    assert alert.severity == "high"
    assert alert.entities["users"] == ["alice@example.com"]
    assert alert.metadata["rule"] == "AUTH-001"
