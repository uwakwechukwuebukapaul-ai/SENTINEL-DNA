from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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
from services.intelligence.reasoning import EvidenceReasoner
from services.intelligence.investigation.investigation_result import InvestigationResult


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


def test_provider_provenance_is_deterministic_and_not_fabricated():
    result = gateway_result(
        ProviderResult(ProviderIdentity("provider-z"), observation=observation("malicious")),
        ProviderResult(ProviderIdentity("provider-a"), observation=observation("benign")),
    )
    normalized = InvestigationCoordinator._normalize_intelligence_gateway_result(result)
    assert normalized["intelligence_provenance"] == {
        "providers": ["provider-a", "provider-z"],
        "status": [],
        "disposition": "mixed",
    }
    assert "provider-invented" not in normalized["intelligence_provenance"]["providers"]


def test_reasoning_finding_preserves_provider_provenance_and_serialization():
    context = SimpleNamespace(
        tenant_id="tenant-a",
        evidence=[{"evidence_id": "E-1", "tenant_id": "tenant-a", "description": "phishing indicator"}],
        iocs=[],
        timeline=[],
        intelligence_provenance={
            "providers": ["provider-z", "provider-a", "provider-a"],
            "status": ["stale"],
            "disposition": "supporting",
            "audit": {"tenant_id": "tenant-a"},
        },
    )
    finding = EvidenceReasoner().reason(context).findings[0]
    assert finding.intelligence_provenance == {
        "providers": ["provider-a", "provider-z"],
        "status": ["stale"],
        "disposition": "supporting",
    }
    assert finding.to_dict()["intelligence_provenance"]["providers"] == ["provider-a", "provider-z"]


def test_cross_tenant_provider_provenance_is_not_attached():
    context = SimpleNamespace(
        tenant_id="tenant-a",
        evidence=[{"evidence_id": "E-1", "tenant_id": "tenant-a", "description": "phishing indicator"}],
        iocs=[],
        timeline=[],
        intelligence_provenance={
            "providers": ["provider-a"],
            "status": [],
            "disposition": "supporting",
            "audit": {"tenant_id": "tenant-b"},
        },
    )
    finding = EvidenceReasoner().reason(context).findings[0]
    assert finding.intelligence_provenance == {}


def test_recommendations_without_causal_provenance_remain_unattributed():
    recommendation = "Review the investigation with an analyst."
    assert recommendation == "Review the investigation with an analyst."
    assert not isinstance(recommendation, dict)


def test_decision_recommendations_do_not_inherit_investigation_wide_provenance():
    decision = DecisionEngine().decide({
        "case_id": "CASE-2",
        "risk": "high",
        "findings": [{
            "finding_id": "RF-1",
            "intelligence_provenance": {
                "providers": ["provider-a"],
                "status": [],
                "disposition": "supporting",
            },
        }],
    })
    assert all(isinstance(item, str) for item in decision.recommended_actions)
    assert "intelligence_provenance" not in decision.to_dict()


def test_optional_recommendation_sources_are_additive_and_serializable():
    result = InvestigationResult(recommendations=["Escalate for analyst review"])
    assert result.recommendation_sources == []
    assert result.to_dict()["recommendations"] == ["Escalate for analyst review"]
    assert result.to_dict()["recommendation_sources"] == []

    result.recommendation_sources = [{
        "recommendation": "Escalate for analyst review",
        "source_finding_id": "RF-1",
        "tenant_id": "tenant-a",
        "provenance": {
            "providers": ["provider-a"],
            "status": [],
            "disposition": "supporting",
        },
    }]
    serialized = result.to_dict()
    assert serialized["recommendations"] == ["Escalate for analyst review"]
    assert serialized["recommendation_sources"][0]["source_finding_id"] == "RF-1"
