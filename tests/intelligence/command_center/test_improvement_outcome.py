from services.intelligence.command_center.improvement_outcome_service import ImprovementOutcomeIntelligenceService


def test_deterministic_outcomes_and_bounded_progress():
    data={"programs":[{"tenant_id":"t1","program_id":"p1","dimension":"Evidence","priority":"high","status":"improving","current_score":70,"score_delta":10,"confidence":.8,"evidence_strength":"strong"}]}
    service=ImprovementOutcomeIntelligenceService(); a=service.derive("t1",data); b=service.derive("t1",data)
    assert a==b and a["outcomes"][0]["outcome_classification"]=="meaningful_improvement"
    assert 0 <= a["summary"]["overall_progress"] <= 100 and a["advisory_only"] is True


def test_missing_measurement_and_regression():
    data={"programs":[{"tenant_id":"t1","program_id":"p1","dimension":"Evidence","priority":"high"},{"tenant_id":"t1","program_id":"p2","dimension":"Quality","priority":"medium","current_score":40,"score_delta":-5}]}
    result=ImprovementOutcomeIntelligenceService().derive("t1",data)
    assert {x["outcome_classification"] for x in result["outcomes"]}=={"not_yet_measurable","regression"}
    assert result["summary"]["regressions"]==1


def test_tenant_isolation():
    result=ImprovementOutcomeIntelligenceService().derive("t1",{"programs":[{"tenant_id":"t2","program_id":"p","dimension":"x"}]})
    assert result["outcomes"]==[] and result["summary"]["total_programs"]==0
