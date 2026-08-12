import json
from pathlib import Path

import pytest

from sentinel_dna.investigation import InvestigationCoordinator
from sentinel_dna.telemetry import (
    JSONTelemetryAdapter,
    SecurityAlert,
    SentinelTelemetryAdapter,
    TelemetryAdapter,
    TelemetryIngestionGateway,
    TelemetryIngestionResult,
)


def sentinel_event():
    return {
        "SystemAlertId": "SENTINEL-GW-001",
        "AlertName": "Suspicious Authentication Activity",
        "Description": (
            "Multiple suspicious authentication attempts detected. "
            "Verify activity at https://example-login.com/security."
        ),
        "Severity": "High",
        "TimeGenerated": "2026-08-12T00:00:00Z",
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
        ],
        "Tactics": ["CredentialAccess"],
        "Techniques": ["T1110"],
        "ExtendedProperties": {
            "RuleId": "AUTH-001",
        },
    }


def json_event():
    return {
        "id": "JSON-GW-001",
        "source": "demo-soc",
        "timestamp": "2026-08-12T00:00:00Z",
        "title": "Suspicious Authentication Activity",
        "severity": "high",
        "description": (
            "Suspicious authentication activity detected."
        ),
        "entities": {
            "users": ["alice@example.com"],
            "hosts": ["WORKSTATION-01"],
            "ips": ["203.0.113.50"],
            "domains": ["example-login.com"],
            "hashes": [],
        },
    }


def build_gateway(tmp_path):
    coordinator = InvestigationCoordinator(Path(tmp_path))

    return TelemetryIngestionGateway(
        adapters={
            "sentinel": SentinelTelemetryAdapter(),
            "json": JSONTelemetryAdapter(),
        },
        investigation_coordinator=coordinator,
    )


def test_gateway_registers_adapters(tmp_path):
    gateway = build_gateway(tmp_path)

    assert gateway.adapters == ("json", "sentinel")


def test_gateway_normalizes_sentinel_event(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
    )

    assert isinstance(result, TelemetryIngestionResult)
    assert result.success is True
    assert result.adapter == "sentinel"
    assert result.alert is not None
    assert isinstance(result.alert, SecurityAlert)
    assert result.alert.alert_id == "SENTINEL-GW-001"
    assert result.alert.severity == "high"
    assert result.investigation is None
    assert result.errors == []


def test_gateway_supports_multiple_adapters(tmp_path):
    gateway = build_gateway(tmp_path)

    sentinel_result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
    )

    json_result = gateway.ingest(
        json_event(),
        adapter="json",
    )

    assert sentinel_result.success is True
    assert sentinel_result.alert.alert_id == "SENTINEL-GW-001"

    assert json_result.success is True
    assert json_result.alert.alert_id == "JSON-GW-001"


def test_gateway_adapter_selection_is_case_insensitive(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="  SENTINEL  ",
    )

    assert result.success is True
    assert result.adapter == "sentinel"


def test_gateway_rejects_unsupported_adapter(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="splunk",
    )

    assert result.success is False
    assert result.alert is None
    assert result.errors[0]["stage"] == "adapter_selection"
    assert result.errors[0]["type"] == "UnsupportedAdapterError"


@pytest.mark.parametrize(
    "adapter",
    [
        "",
        "   ",
        None,
    ],
)
def test_gateway_rejects_invalid_adapter_name(tmp_path, adapter):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter=adapter,
    )

    assert result.success is False
    assert result.alert is None
    assert result.adapter == (
        adapter.strip().lower()
        if isinstance(adapter, str)
        else ""
    )
    assert result.errors[0]["stage"] == "adapter_selection"
    assert result.errors[0]["type"] == "ValueError"
    assert result.errors[0]["message"] == (
        "adapter must be a non-empty string"
    )


def test_gateway_converts_validation_error_to_structured_result(
    tmp_path,
):
    gateway = build_gateway(tmp_path)

    invalid_event = sentinel_event()
    invalid_event.pop("SystemAlertId")

    result = gateway.ingest(
        invalid_event,
        adapter="sentinel",
    )

    assert result.success is False
    assert result.alert is None
    assert result.errors[0]["stage"] == "normalization"
    assert result.errors[0]["type"] == "TelemetryValidationError"
    assert "missing required alert ID" in result.errors[0]["message"]


def test_gateway_requires_case_id_for_investigation(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        investigate=True,
    )

    assert result.success is False
    assert result.errors[0]["stage"] == "investigation_validation"
    assert result.errors[0]["type"] == "ValueError"
    assert "case_id is required" in result.errors[0]["message"]


def test_gateway_requires_non_empty_case_id(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        case_id="   ",
        investigate=True,
    )

    assert result.success is False
    assert result.errors[0]["stage"] == "investigation_validation"
    assert result.errors[0]["type"] == "ValueError"
    assert "case_id cannot be empty" in result.errors[0]["message"]


def test_gateway_strips_case_id_before_investigation(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        case_id="  gateway-normalized-001  ",
        investigate=True,
    )

    assert result.success is True
    assert result.investigation is not None
    assert result.investigation.results["case_id"] == (
        "gateway-normalized-001"
    )


def test_gateway_hands_off_to_ai_investigator(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        case_id="gateway-investigation-001",
        investigate=True,
    )

    assert result.success is True
    assert result.alert is not None
    assert result.investigation is not None

    investigation = result.investigation

    assert investigation.plan_name == "ai-investigator-v1"
    assert investigation.errors == []
    assert investigation.results["case_id"] == (
        "gateway-investigation-001"
    )
    assert len(investigation.results["tasks"]) == 15


def test_gateway_returns_alert_when_investigation_handoff_fails(
    tmp_path,
):
    class FailingCoordinator:
        def investigate(self, case_id, alert):
            raise RuntimeError("investigation backend unavailable")

    gateway = TelemetryIngestionGateway(
        adapters={
            "sentinel": SentinelTelemetryAdapter(),
        },
        investigation_coordinator=FailingCoordinator(),
    )

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        case_id="gateway-failure-001",
        investigate=True,
    )

    assert result.success is False
    assert result.alert is not None
    assert result.alert.alert_id == "SENTINEL-GW-001"
    assert result.investigation is None
    assert result.errors[0]["stage"] == "investigation_handoff"
    assert result.errors[0]["type"] == "RuntimeError"
    assert result.errors[0]["message"] == (
        "investigation backend unavailable"
    )


def test_gateway_fails_cleanly_without_investigation_coordinator(
    tmp_path,
):
    gateway = TelemetryIngestionGateway(
        adapters={
            "sentinel": SentinelTelemetryAdapter(),
        },
    )

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        case_id="gateway-no-coordinator-001",
        investigate=True,
    )

    assert result.success is False
    assert result.alert is not None
    assert result.alert.alert_id == "SENTINEL-GW-001"
    assert result.investigation is None
    assert result.errors[0]["stage"] == "investigation_handoff"
    assert result.errors[0]["type"] == "RuntimeError"
    assert "not configured" in result.errors[0]["message"]


def test_gateway_rejects_adapter_returning_wrong_contract(
    tmp_path,
):
    class InvalidAdapter(TelemetryAdapter):
        def normalize(self, raw_event):
            return {
                "alert_id": "INVALID",
            }

    gateway = TelemetryIngestionGateway(
        adapters={
            "invalid": InvalidAdapter(),
        },
    )

    result = gateway.ingest(
        {},
        adapter="invalid",
    )

    assert result.success is False
    assert result.alert is None
    assert result.errors[0]["stage"] == (
        "normalization_contract"
    )
    assert result.errors[0]["type"] == (
        "TelemetryAdapterContractError"
    )
    assert result.errors[0]["message"] == (
        "telemetry adapter must return SecurityAlert"
    )


def test_gateway_requires_at_least_one_adapter():
    with pytest.raises(
        ValueError,
        match="at least one telemetry adapter",
    ):
        TelemetryIngestionGateway({})


def test_gateway_rejects_invalid_registered_adapter_name():
    with pytest.raises(
        ValueError,
        match="adapter names must be non-empty strings",
    ):
        TelemetryIngestionGateway(
            {
                "   ": SentinelTelemetryAdapter(),
            }
        )


def test_gateway_rejects_non_adapter_registration():
    with pytest.raises(
        TypeError,
        match="must implement TelemetryAdapter",
    ):
        TelemetryIngestionGateway(
            {
                "sentinel": object(),
            }
        )


def test_gateway_rejects_duplicate_normalized_adapter_names():
    with pytest.raises(
        ValueError,
        match="duplicate adapter name after normalization",
    ):
        TelemetryIngestionGateway(
            {
                "Sentinel": SentinelTelemetryAdapter(),
                " sentinel ": SentinelTelemetryAdapter(),
            }
        )


def test_gateway_result_is_serializable(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
        case_id="gateway-serialization-001",
        investigate=True,
    )

    serialized = result.to_dict()

    assert serialized["success"] is True
    assert serialized["adapter"] == "sentinel"
    assert serialized["alert"]["alert_id"] == "SENTINEL-GW-001"
    assert serialized["investigation"]["plan_name"] == (
        "ai-investigator-v1"
    )

    json.dumps(serialized)


def test_gateway_error_result_is_serializable(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="unsupported",
    )

    serialized = result.to_dict()

    assert serialized["success"] is False
    assert serialized["adapter"] == "unsupported"
    assert serialized["alert"] is None
    assert serialized["investigation"] is None
    assert serialized["errors"][0]["stage"] == (
        "adapter_selection"
    )

    json.dumps(serialized)


def test_gateway_does_not_investigate_by_default(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        sentinel_event(),
        adapter="sentinel",
    )

    assert result.success is True
    assert result.investigation is None


def test_gateway_exposes_available_adapter_names(tmp_path):
    gateway = build_gateway(tmp_path)

    assert "sentinel" in gateway.adapters
    assert "json" in gateway.adapters


def test_gateway_adapter_names_are_deterministic(tmp_path):
    gateway = TelemetryIngestionGateway(
        adapters={
            " ZETA ": SentinelTelemetryAdapter(),
            "alpha": JSONTelemetryAdapter(),
            "Bravo": SentinelTelemetryAdapter(),
        }
    )

    assert gateway.adapters == (
        "alpha",
        "bravo",
        "zeta",
    )


def test_gateway_preserves_json_adapter_contract(tmp_path):
    gateway = build_gateway(tmp_path)

    result = gateway.ingest(
        json_event(),
        adapter="json",
    )

    assert result.success is True
    assert result.alert is not None
    assert result.alert.alert_id == "JSON-GW-001"
    assert result.alert.source == "demo-soc"
    assert result.alert.entities["users"] == [
        "alice@example.com"
    ]
