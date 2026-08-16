from datetime import datetime, timezone

from app.intelligence.gateway import IOC, IOCType, IntelligenceObservation, ProviderIdentity
from services.intelligence.investigation.investigation_orchestrator import InvestigationOrchestrator


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def observation(ioc, provider, reputation):
    return IntelligenceObservation(ioc, ProviderIdentity(provider), datetime.now(timezone.utc), reputation=reputation, confidence=.9)


def test_fused_intelligence_enters_reasoning_as_auditable_evidence():
    ioc = IOC("evil.test", IOCType.DOMAIN)
    result = InvestigationOrchestrator().investigate(
        [{"value": ioc.value, "type": ioc.type.value}],
        case_id="CASE-1",
        context={"tenant_id": "tenant-a"},
        ioc=ioc,
        intelligence_observations=[observation(ioc, "alpha", "malicious"), observation(ioc, "beta", "malicious")],
    )
    assert result.success is True
    assert result.fusion["status"] == "MALICIOUS"
    assert result.fusion["provenance"]
    assert result.reasoning["metadata"]["intelligence_reasoning_input"]["category"] == "FUSED_ASSESSMENT"
    assert result.reasoning["metadata"]["intelligence_reasoning_input"]["policy_version"] == "fusion-v1"


def test_no_intelligence_continues_without_benign_inference():
    ioc = IOC("unknown.test", IOCType.DOMAIN)
    result = InvestigationOrchestrator().investigate(
        [], case_id="CASE-2", context={"tenant_id": "tenant-a"}, ioc=ioc, intelligence_observations=[]
    )
    assert result.success is True
    assert result.fusion["status"] == "NO_INTELLIGENCE"
    assert result.reasoning["metadata"]["intelligence_reasoning_input"]["category"] == "NO_INTELLIGENCE"
    assert result.fusion["aggregate_reputation"] == "unknown"


def test_disagreement_remains_visible_to_reasoning():
    ioc = IOC("split.test", IOCType.DOMAIN)
    result = InvestigationOrchestrator().investigate(
        [], case_id="CASE-3", context={"tenant_id": "tenant-a"}, ioc=ioc,
        intelligence_observations=[observation(ioc, "alpha", "malicious"), observation(ioc, "beta", "benign")],
    )
    assert result.fusion["status"] == "CONFLICTED"
    assert set(result.reasoning["metadata"]["intelligence_reasoning_input"]["conflicting_providers"]) == {"alpha", "beta"}
