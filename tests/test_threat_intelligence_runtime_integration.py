from datetime import datetime, timezone

import pytest

from app.intelligence.gateway import (
    IOCType, IntelligenceObservation, ProviderIdentity, ProviderResult,
    ThreatIntelligenceGateway,
)
from services.intelligence.orchestration.investigation_coordinator import InvestigationCoordinator
import services.intelligence.orchestration.investigation_coordinator as coordinator_module
import services.observability.service as observability_service


class DeterministicProvider:
    identity = ProviderIdentity("deterministic-test")
    calls = 0

    def capabilities(self):
        return frozenset({IOCType.IP, IOCType.DOMAIN, IOCType.HASH})

    def lookup(self, request):
        self.calls += 1
        return ProviderResult(self.identity, IntelligenceObservation(
            request.ioc, self.identity, datetime(2026, 1, 1, tzinfo=timezone.utc),
            provider_record="deterministic-record", confidence=0.75,
        ))


def test_canonical_coordinator_routes_ioc_once_and_preserves_identity():
    provider = DeterministicProvider()
    seen = []
    gateway = ThreatIntelligenceGateway([provider], lambda tenant, actor: seen.append((tenant, actor)) or tenant == "tenant-a")
    coordinator = InvestigationCoordinator(threat_intelligence_gateway=gateway)
    result = coordinator.investigate("case-1", {"kind": "alert"}, iocs=[
        {"type": "domain", "value": "example.test"},
        {"type": "domain", "value": "EXAMPLE.TEST"},
    ], tenant_id="tenant-a", actor_id="actor-a")
    assert provider.calls == 1
    assert seen == [("tenant-a", "actor-a")]
    assert result.plan_name == "Standard Security Investigation"
    assert "results" in result.to_dict() and "errors" in result.to_dict()


def test_authorization_failure_is_not_downgraded():
    gateway = ThreatIntelligenceGateway([DeterministicProvider()], lambda *_: False)
    with pytest.raises(PermissionError):
        InvestigationCoordinator(threat_intelligence_gateway=gateway).investigate(
            "case-2", {}, iocs=[{"type": "domain", "value": "example.test"}],
            tenant_id="tenant-a", actor_id="actor-a",
        )


def test_authorization_failure_preserves_exact_message_and_emits_safe_diagnostic(monkeypatch):
    events = []

    class Observer:
        def event(self, name, **fields):
            events.append((name, fields))

    monkeypatch.setattr(coordinator_module, "ObservabilityService", Observer)
    gateway = ThreatIntelligenceGateway([DeterministicProvider()], lambda *_: False)
    with pytest.raises(PermissionError, match="^actor is not authorized for threat intelligence lookup$"):
        InvestigationCoordinator(threat_intelligence_gateway=gateway).investigate(
            "case-3", {}, iocs=[{"type": "domain", "value": "example.test"}],
            tenant_id="tenant-a", actor_id="actor-a",
        )
    assert events[-1] == ("THREAT_INTELLIGENCE_AUTHORIZATION_DENIED", {
        "case_id": "case-3", "tenant_id": "tenant-a", "actor_id": "actor-a",
        "ioc_type": "domain", "reason": "gateway authorization denied",
    })
    assert "example.test" not in str(events)


def test_authorization_denial_does_not_return_result_or_call_provider():
    provider = DeterministicProvider()
    gateway = ThreatIntelligenceGateway([provider], lambda *_: False)
    with pytest.raises(PermissionError):
        InvestigationCoordinator(threat_intelligence_gateway=gateway).investigate(
            "case-4", {}, iocs=[{"type": "domain", "value": "example.test"}],
            tenant_id="tenant-a", actor_id="actor-a",
        )
    assert provider.calls == 0


def test_observability_failure_cannot_mask_permission_error(monkeypatch):
    class FailingLogger:
        def info(self, *args, **kwargs):
            raise RuntimeError("telemetry failed")

    monkeypatch.setattr(
        coordinator_module,
        "ObservabilityService",
        lambda: observability_service.ObservabilityService(FailingLogger()),
    )
    gateway = ThreatIntelligenceGateway([DeterministicProvider()], lambda *_: False)
    with pytest.raises(PermissionError, match="^actor is not authorized for threat intelligence lookup$"):
        InvestigationCoordinator(threat_intelligence_gateway=gateway).investigate(
            "case-5", {}, iocs=[{"type": "domain", "value": "example.test"}],
            tenant_id="tenant-a", actor_id="actor-a",
        )
