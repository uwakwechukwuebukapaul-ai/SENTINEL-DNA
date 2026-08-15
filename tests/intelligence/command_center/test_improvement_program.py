from services.intelligence.command_center.improvement_program_service import ImprovementProgramAnalyticsService


def test_deterministic_empty_programs():
    service = ImprovementProgramAnalyticsService()
    a = service.derive("t1", improvement={"priority_signals": [], "improvement_plans": [], "comparative_dimensions": []})
    assert a == service.derive("t1", improvement={"priority_signals": [], "improvement_plans": [], "comparative_dimensions": []})
    assert a["summary"]["total_programs"] == 0
    assert a["advisory_only"] is True


def test_not_yet_measurable_program_and_isolation():
    improvement = {"priority_signals": [{"tenant_id": "t1", "dimension_id": "d1", "dimension_name": "Evidence", "priority": "high", "trend": "stable", "confidence": .5, "evidence_strength": "weak", "uncertainty": []}], "improvement_plans": [], "comparative_dimensions": [{"tenant_id": "t1", "dimension_id": "d1", "current_score_or_state": "weak"}]}
    result = ImprovementProgramAnalyticsService().derive("t1", improvement=improvement)
    assert result["programs"][0]["status"] == "not_yet_measurable"
    assert result["programs"][0]["effectiveness"] == "indeterminate"
    assert result["programs"][0]["advisory_only"] is True


def test_tenant_filtering():
    result = ImprovementProgramAnalyticsService().derive("t1", improvement={"priority_signals": [{"tenant_id": "t2", "dimension_id": "d", "priority": "high"}], "improvement_plans": [], "comparative_dimensions": []})
    assert result["programs"] == []
