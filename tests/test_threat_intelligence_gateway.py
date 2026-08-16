from datetime import timedelta

import pytest

from app.intelligence.gateway import *


class FakeProvider:
    def __init__(self, name, fn):
        self.identity = ProviderIdentity(name)
        self.fn = fn

    def capabilities(self):
        return frozenset(IOCType)

    def lookup(self, request):
        return self.fn(self.identity, request)


def observation(identity, request, reputation="unknown"):
    return ProviderResult(identity, IntelligenceObservation(request.ioc, identity, __import__("app.intelligence.gateway", fromlist=["_utc_now"])._utc_now(), reputation=reputation))


def test_multiple_providers_are_sorted_and_preserved():
    request = LookupRequest("tenant-a", "analyst", IOC("Example.COM", IOCType.DOMAIN))
    gateway = ThreatIntelligenceGateway([FakeProvider("zeta", observation), FakeProvider("alpha", observation)], lambda *_: True)
    result = gateway.lookup(request)
    assert [r.provider.name for r in result.provider_results] == ["alpha", "zeta"]
    assert len(result.observations) == 2


def test_failure_isolated_and_authorization_enforced():
    request = LookupRequest("tenant-a", "analyst", IOC("1.2.3.4", IOCType.IP))
    gateway = ThreatIntelligenceGateway([FakeProvider("bad", lambda *_: (_ for _ in ()).throw(TimeoutError())), FakeProvider("good", observation)], lambda t, a: t == "tenant-a")
    result = gateway.lookup(request)
    assert result.provider_results[0].error.code == ProviderErrorCode.TIMEOUT
    assert result.successful
    with pytest.raises(PermissionError):
        gateway.lookup(LookupRequest("tenant-b", "analyst", request.ioc))


def test_stale_is_explicit_and_evidence_does_not_change_case_verdict():
    request = LookupRequest("tenant-a", "analyst", IOC("bad.test", IOCType.DOMAIN))
    provider = FakeProvider("fake", lambda identity, req: ProviderResult(identity, IntelligenceObservation(req.ioc, identity, __import__("app.intelligence.gateway", fromlist=["_utc_now"])._utc_now(), expires_at=__import__("app.intelligence.gateway", fromlist=["_utc_now"])._utc_now() - timedelta(seconds=1))))
    case = {"case_id": "C-1", "status": "OPEN", "risk_score": 10, "confidence": 0}
    ThreatIntelligenceGateway([provider], lambda *_: True).add_to_case_evidence(case, request)
    assert case["status"] == "OPEN" and case["risk_score"] == 10 and case["confidence"] == 0
    assert case["evidence"][0]["type"] == "THREAT_INTELLIGENCE"
