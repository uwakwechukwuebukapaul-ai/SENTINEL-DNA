from services.intelligence.fusion import IntelligenceDecisionGovernance


def test_governance_is_advisory_and_preserves_conflict():
    result = IntelligenceDecisionGovernance().evaluate({
        "status": "CONFLICTED", "conflicting_providers": ["a", "b"],
        "provenance": [{"provider": "a"}], "aggregate_confidence": .4,
    }, {"tenant_id": "tenant-a", "investigation_id": "inv-1"})
    assert result.state == "CONTRADICTING"
    assert result.decision_influence == "ADVISORY_ONLY"
    assert result.tenant_id == "tenant-a"
    assert result.provenance_references == ({"provider": "a"},)


def test_no_intelligence_is_first_class_and_not_benign():
    result = IntelligenceDecisionGovernance().evaluate({"status": "NO_INTELLIGENCE"})
    assert result.state == "NO_INTELLIGENCE"
    assert result.fusion_status == "NO_INTELLIGENCE"
    assert result.decision_influence == "ADVISORY_ONLY"


def test_stale_and_malformed_intelligence_fail_closed():
    stale = IntelligenceDecisionGovernance().evaluate({"status": "MALICIOUS", "stale_providers": ["old"]})
    malformed = IntelligenceDecisionGovernance().evaluate({})
    assert stale.state == "STALE_INTELLIGENCE"
    assert malformed.state == "INVALID_INTELLIGENCE"


def test_governance_does_not_mutate_input():
    fusion = {"status": "BENIGN", "supporting_providers": ["a"]}
    before = dict(fusion)
    IntelligenceDecisionGovernance().evaluate(fusion)
    assert fusion == before
