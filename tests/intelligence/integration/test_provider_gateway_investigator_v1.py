from datetime import datetime, timezone

import pytest

from app.intelligence.gateway import (
    IOC,
    IOCType,
    IntelligenceObservation,
    LookupRequest,
    ProviderError,
    ProviderErrorCode,
    ProviderIdentity,
    ProviderResult,
    ThreatIntelligenceGateway,
)
from services.core.application_container import build_container
from services.intelligence.fusion import ProviderNeutralFusionEngine
from services.intelligence.orchestration.investigation_coordinator import InvestigationCoordinator


NOW = datetime.now(timezone.utc)


class Runtime:
    def available(self, _capability):
        return True

    def execute(self, _task):
        return {"findings": [], "recommendations": [], "metadata": {}, "artifacts": {}}


class Provider:
    def __init__(self, name, reputation="malicious", error=None):
        self.identity = ProviderIdentity(name, "test")
        self.reputation = reputation
        self.error = error
        self.requests = []

    def capabilities(self):
        return frozenset({IOCType.IP, IOCType.DOMAIN, IOCType.HASH})

    def lookup(self, request):
        self.requests.append(request)
        if self.error is not None:
            return ProviderResult(self.identity, error=self.error)
        return ProviderResult(
            self.identity,
            IntelligenceObservation(
                request.ioc,
                self.identity,
                NOW,
                reputation=self.reputation,
                confidence=0.8,
            ),
        )


def _gateway(*providers, authorized=True):
    return ThreatIntelligenceGateway(providers, lambda *_: authorized)


def _coordinator(gateway):
    return InvestigationCoordinator(
        runtime=Runtime(),
        threat_intelligence_gateway=gateway,
        provider_neutral_fusion_engine=ProviderNeutralFusionEngine(),
    )


def test_application_container_injects_offline_gateway_and_fusion_without_providers():
    container = build_container()
    coordinator = container.require("investigation_coordinator")
    assert coordinator.threat_intelligence_gateway is container.require("threat_intelligence_gateway")
    assert coordinator.provider_neutral_fusion_engine is container.require("provider_neutral_fusion_engine")
    assert coordinator.threat_intelligence_gateway._providers == ()


def test_canonical_coordinator_invokes_gateway_fusion_and_preserves_tenant_actor_correlation():
    provider = Provider("provider-a")
    coordinator = _coordinator(_gateway(provider))
    result = coordinator.investigate(
        "case-provider",
        {},
        iocs=[{"type": "domain", "value": "example.test"}],
        tenant_id="tenant-a",
        actor_id="actor-a",
        correlation_id="corr-a",
    )

    assert result.success is True
    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert (request.tenant_id, request.actor_id, request.correlation_id) == (
        "tenant-a",
        "actor-a",
        "corr-a",
    )
    status = result.intelligence["normalized"]["metadata"]["intelligence_status"]
    assert status["intelligence_provenance"] == {
        "providers": ["provider-a"],
        "status": [],
        "disposition": "supporting",
    }
    assert status["fusion"]["tenant_id"] == "tenant-a"
    assert status["fusion"]["investigation_id"] == "case-provider"
    report = result.intelligence["report"]
    assert report["metadata"]["intelligence_provenance"]["providers"] == ["provider-a"]
    assert report["metadata"]["intelligence_fusion"]["status"] == "MALICIOUS"


def test_multiple_providers_are_fused_deterministically_and_conflict_remains_visible():
    coordinator = _coordinator(_gateway(Provider("provider-z"), Provider("provider-a", "benign")))
    result = coordinator.investigate(
        "case-conflict",
        {},
        iocs=[{"type": "domain", "value": "split.test"}],
        tenant_id="tenant-a",
        actor_id="actor-a",
    )
    status = result.intelligence["normalized"]["metadata"]["intelligence_status"]
    assert status["intelligence_provenance"]["providers"] == ["provider-a", "provider-z"]
    assert status["intelligence_provenance"]["disposition"] == "mixed"
    assert status["fusion"]["status"] == "CONFLICTED"


def test_provider_failure_is_preserved_without_fabricated_intelligence():
    provider = Provider("provider-timeout", error=ProviderError(ProviderErrorCode.TIMEOUT, "timed out", True))
    coordinator = _coordinator(_gateway(provider))
    result = coordinator.investigate(
        "case-timeout",
        {},
        iocs=[{"type": "domain", "value": "timeout.test"}],
        tenant_id="tenant-a",
        actor_id="actor-a",
    )
    status = result.intelligence["normalized"]["metadata"]["intelligence_status"]
    assert status["statuses"] == ["unavailable"]
    assert status["disposition"] == "unavailable"
    assert status["provider_results"][0]["error"]["code"] == ProviderErrorCode.TIMEOUT
    assert status["fusion"]["status"] == "NO_INTELLIGENCE"
    assert status["fusion"]["unavailable_providers"] == ["provider-timeout"]
    assert result.intelligence["report"]["metadata"]["intelligence_provider_errors"] == [{
        "provider": "provider-timeout",
        "code": "timeout",
        "retryable": True,
    }]


def test_authorization_happens_before_provider_execution_and_preserves_permission_error():
    provider = Provider("provider-a")
    coordinator = _coordinator(_gateway(provider, authorized=False))
    with pytest.raises(PermissionError, match="^actor is not authorized for threat intelligence lookup$"):
        coordinator.investigate(
            "case-denied",
            {},
            iocs=[{"type": "domain", "value": "denied.test"}],
            tenant_id="tenant-a",
            actor_id="actor-a",
        )
    assert provider.requests == []


def test_invalid_ioc_type_is_fail_closed_as_unknown_without_provider_call():
    provider = Provider("provider-a")
    result = _coordinator(_gateway(provider)).investigate(
        "case-invalid-ioc",
        {},
        iocs=[{"type": "not-a-real-type", "value": "indicator"}],
        tenant_id="tenant-a",
        actor_id="actor-a",
    )
    assert result.success is True
    assert provider.requests == []
    status = result.intelligence["normalized"]["metadata"]["intelligence_status"]
    assert status["disposition"] == "unavailable"


def test_gateway_result_audit_preserves_correlation_without_credentials_or_raw_payload():
    ioc = IOC("example.test", IOCType.DOMAIN)
    request = LookupRequest(
        "tenant-a", "actor-a", ioc, correlation_id="corr-a"
    )
    result = _gateway(Provider("provider-a")).lookup(request)
    assert result.audit.correlation_id == "corr-a"
    assert "authorization" not in repr(result).lower()
    assert "api_key" not in repr(result).lower()
