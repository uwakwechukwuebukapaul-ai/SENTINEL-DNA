import warnings
from datetime import datetime, timezone
import pytest
from app.intelligence.gateway import IOC, IOCType, LookupRequest, ProviderIdentity, ProviderResult, IntelligenceObservation, ThreatIntelligenceGateway
from services.investigation.context import InvestigationContext
from threat_intel import analyze_indicator

class Provider:
    identity = ProviderIdentity("test")
    def capabilities(self): return frozenset({IOCType.DOMAIN})
    def lookup(self, request): return ProviderResult(self.identity, IntelligenceObservation(request.ioc, self.identity, datetime.now(timezone.utc)))

def test_legacy_path_is_disabled_without_network():
    with warnings.catch_warnings(record=True) as caught:
        result = analyze_indicator("https://example.test")
    assert result["status"] == "UNAVAILABLE"
    assert caught

def test_gateway_preserves_tenant_provenance_into_context():
    request = LookupRequest("tenant-a", "actor-a", IOC("example.test", IOCType.DOMAIN))
    context = InvestigationContext("investigation-1", "tenant-a", "actor-a")
    case = {"case_id": "C-1", "status": "OPEN", "risk_score": 1, "confidence": 0}
    result = ThreatIntelligenceGateway([Provider()], lambda t, a: (t, a) == ("tenant-a", "actor-a")).add_to_case_evidence(case, request, context)
    assert result.audit.tenant_id == "tenant-a"
    assert context.evidence[0]["audit"]["tenant_id"] == "tenant-a"
    with pytest.raises(PermissionError): context.add_evidence({}, "tenant-b")
