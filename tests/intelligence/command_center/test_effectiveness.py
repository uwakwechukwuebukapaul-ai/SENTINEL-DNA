from services.intelligence.command_center.effectiveness_service import AnalystLearningEffectivenessService


def row(tenant="a", kind="evidence_gap", timestamp="2026-01-01", **kw):
    value={"tenant_id":tenant,"learning_type":kind,"learning_id":f"l-{timestamp}","timestamp":timestamp,"quality_metrics":{"evidence_insufficiency_rate":kw.pop("evidence", .8),"disagreement_rate":kw.pop("disagreement", 0),"unresolved_rate":kw.pop("unresolved", 0),"human_review_rate":0,"confidence":kw.pop("confidence", .5)},"contributing_feedback_ids":[f"f-{timestamp}"],"contributing_investigation_ids":[f"i-{timestamp}"],"uncertainty":[],"contributing_outcome_references":kw.pop("outcomes",[]) }
    value.update(kw); return value


def test_effectiveness_is_deterministic_and_stable_id_is_tenant_scoped():
    observations=[row(timestamp="2026-01-01"),row(timestamp="2026-02-01",evidence=.2,confidence=.9)]
    service=AnalystLearningEffectivenessService(); first=service.derive("a",observations); second=service.derive("a",observations)
    assert [x.to_dict() for x in first]==[x.to_dict() for x in second] and first[0].classification=="improving"
    assert first[0].effectiveness_id != service.derive("b",[dict(x,tenant_id="b") for x in observations])[0].effectiveness_id


def test_effectiveness_classifications_cover_degradation_stability_and_mixed():
    service=AnalystLearningEffectivenessService()
    assert service.derive("a",[row(),row(timestamp="2026-02-01",evidence=.9)])[0].classification=="degrading"
    assert service.derive("a",[row(),row(timestamp="2026-02-01",evidence=.82)])[0].classification=="stable"
    mixed=[row(disagreement=0,evidence=.8),row(timestamp="2026-02-01",disagreement=1,evidence=.2)]
    assert service.derive("a",mixed)[0].classification=="mixed"


def test_effectiveness_is_explicitly_insufficient_without_temporal_evidence():
    result=AnalystLearningEffectivenessService().derive("a",[row()])[0]
    assert result.classification=="insufficient_data" and "insufficient_observations" in result.uncertainty


def test_effectiveness_preserves_provenance_and_does_not_fabricate_outcomes():
    result=AnalystLearningEffectivenessService().derive("a",[row(),row(timestamp="2026-02-01",evidence=.2)])[0]
    assert result.contributing_outcome_references==[] and "incomplete_provenance" in result.uncertainty


def test_effectiveness_tenant_isolation_and_ordering():
    observations=[row(kind="z",timestamp="2026-01-01"),row(kind="z",timestamp="2026-02-01",evidence=.2),row(kind="a",timestamp="2026-01-01"),row(kind="a",timestamp="2026-02-01",evidence=.2)]
    result=AnalystLearningEffectivenessService().derive("a",observations)
    assert all(x.tenant_id=="a" for x in result) and [x.learning_type for x in result]==["a","z"]
