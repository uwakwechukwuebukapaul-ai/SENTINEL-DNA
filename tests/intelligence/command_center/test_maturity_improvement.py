from services.intelligence.command_center.maturity_improvement_service import MaturityImprovementService


def test_deterministic_comparison_priorities_and_plans():
    report = {"confidence": .7, "evidence_strength": "moderate", "trajectory": "degrading", "uncertainty": [], "provenance": {"source": "test"}, "contributing_references": ["r1"], "dimension_summaries": [{"dimension_id": "a", "display_name": "A", "score": 30, "classification": "degrading", "confidence": .7, "evidence_strength": "moderate", "uncertainty": [], "provenance": {}, "contributing_references": ["r1"]}, {"dimension_id": "b", "display_name": "B", "score": 80, "classification": "improving", "confidence": .8, "evidence_strength": "strong", "uncertainty": [], "provenance": {}, "contributing_references": ["r2"]}]}
    service = MaturityImprovementService()
    a = service.derive("t1", maturity={"tenant_id": "t1", "maturity_score": 55}, report=report)
    b = service.derive("t1", maturity={"tenant_id": "t1", "maturity_score": 55}, report=report)
    assert a == b
    assert a["priority_signals"][0]["priority"] == "high"
    assert a["improvement_plans"][0]["advisory_only"] is True
    assert a["executive_summary"]["weakest_dimension"] == "A"


def test_tenant_isolation_and_empty_data():
    report = {"tenant_id": "t2", "dimension_summaries": []}
    result = MaturityImprovementService().derive("t1", maturity={}, report=report)
    assert result["comparative_dimensions"] == []
    assert result["advisory_only"] is True
