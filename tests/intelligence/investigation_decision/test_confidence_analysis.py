from services.intelligence.investigation_decision.confidence_analysis import ConfidenceAnalysis


def test_confidence_reports_insufficient_evidence():
    assert ConfidenceAnalysis().analyze({})["level"] == "insufficient_evidence"
