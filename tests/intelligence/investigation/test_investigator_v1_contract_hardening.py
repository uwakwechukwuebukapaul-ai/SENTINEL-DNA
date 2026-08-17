from datetime import datetime, timedelta, timezone

from app.intelligence.gateway import (
    GatewayResult,
    IntelligenceObservation,
    IOC,
    IOCType,
    LookupAudit,
    ProviderError,
    ProviderErrorCode,
    ProviderIdentity,
    ProviderResult,
)
from services.intelligence.decision.engine import DecisionEngine
from services.intelligence.investigation.fusion.engine import InvestigationFusionEngine
from services.intelligence.orchestration import InvestigationCoordinator


def gateway_result(*provider_results):
    now = datetime.now(timezone.utc)
    return GatewayResult(
        tuple(r.observation for r in provider_results if r.observation),
        tuple(provider_results),
        LookupAudit("tenant-1", "actor-1", IOC("8.8.8.8", IOCType.IP), ("provider-a",), now, now),
    )


def observation(reputation="malicious", expires_at=None):
    return IntelligenceObservation(
        IOC("8.8.8.8", IOCType.IP),
        ProviderIdentity("provider-a", "1"),
        datetime.now(timezone.utc),
        reputation=reputation,
        expires_at=expires_at,
    )


def test_provider_failure_and_provenance_are_preserved():
    result = gateway_result(
        ProviderResult(
            ProviderIdentity("provider-a"),
            error=ProviderError(ProviderErrorCode.TIMEOUT, "timeout", True),
        )
    )
    normalized = InvestigationCoordinator._normalize_intelligence_gateway_result(result)
    assert normalized["statuses"] == ["unavailable"]
    assert normalized["disposition"] == "unavailable"
    assert normalized["provider_results"][0]["provider"] == "provider-a"
    assert normalized["provider_results"][0]["error"]["code"] == ProviderErrorCode.TIMEOUT
    assert normalized["audit"]["tenant_id"] == "tenant-1"


def test_stale_supporting_contradictory_and_mixed_dispositions():
    stale = gateway_result(ProviderResult(ProviderIdentity("provider-a"), observation=observation(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))))
    assert "stale" in InvestigationCoordinator._normalize_intelligence_gateway_result(stale)["statuses"]
    supporting = InvestigationCoordinator._normalize_intelligence_gateway_result(gateway_result(ProviderResult(ProviderIdentity("provider-a"), observation=observation("malicious"))))
    contradicting = InvestigationCoordinator._normalize_intelligence_gateway_result(gateway_result(ProviderResult(ProviderIdentity("provider-a"), observation=observation("benign"))))
    mixed = gateway_result(ProviderResult(ProviderIdentity("provider-a"), observation=observation("malicious")), ProviderResult(ProviderIdentity("provider-b"), observation=observation("benign")))
    assert supporting["disposition"] == "supporting"
    assert contradicting["disposition"] == "contradicting"
    assert InvestigationCoordinator._normalize_intelligence_gateway_result(mixed)["disposition"] == "mixed"


def test_fusion_preserves_existing_evidence_references_without_fabrication():
    finding = {"id": "F-1", "evidence_references": ["E-1"]}
    fused = InvestigationFusionEngine().fuse("CASE-1", findings=[finding])
    assert fused.findings == [finding]
    assert "evidence_references" not in InvestigationFusionEngine().fuse("CASE-2", findings=[{"id": "F-2"}]).findings[0]


def test_advisory_governance_is_explicit_and_no_action_executes():
    result = DecisionEngine().decide({"case_id": "CASE-1", "risk": "high", "findings": [{"value": "malicious"}]})
    governance = result.to_dict()["metadata"]["governance"]
    assert governance == {"mode": "ADVISORY_ONLY", "analyst_authority_required": True, "autonomous_action": False}
    assert result.synthetic_only is True
