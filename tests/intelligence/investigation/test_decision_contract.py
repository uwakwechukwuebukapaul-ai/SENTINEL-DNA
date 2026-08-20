from services.intelligence.investigation.decision import DecisionIntelligenceEngine


def test_decision_is_normalized_and_evidence_backed():
    result = DecisionIntelligenceEngine().evaluate({
        "investigation_id": "inv-1", "tenant_context": {"tenant_id": "tenant-a"},
        "risk": {"score": 90}, "confidence": 0.8,
        "evidence": [{"evidence_id": "ev-1", "source": "edr", "reason": "Process execution"}, {"source": "raw"}],
    })
    assert result.verdict == "malicious"
    assert result.confidence == 80
    assert result.risk_score == 90
    assert result.supporting_evidence == [{"reference_id": "ev-1", "source": "edr", "reason": "Process execution"}]
    assert result.missing_evidence


def test_missing_identifier_is_never_fabricated():
    result = DecisionIntelligenceEngine().evaluate({"case_id": "case-1", "evidence": [{"source": "sensor"}]})
    assert result.supporting_evidence == []
    assert result.missing_evidence[0]["source"] == "sensor"
