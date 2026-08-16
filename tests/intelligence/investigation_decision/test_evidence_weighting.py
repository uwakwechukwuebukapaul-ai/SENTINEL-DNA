from services.intelligence.investigation_decision.evidence_weighting import EvidenceWeighting


def test_weighting_preserves_noncausal_language():
    assert "causal" in EvidenceWeighting().weight({})["interpretation"]
