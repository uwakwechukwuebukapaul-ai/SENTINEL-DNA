from services.intelligence.command_center.executive_learning_service import AnalystExecutiveLearningService


def trend(kind, classification, confidence=.8, tenant_id="t1", **extra):
    result = dict(tenant_id=tenant_id, trend_type=kind, title=kind, classification=classification,
                direction=classification, confidence=confidence, uncertainty=[],
                provenance={"source": "test"}, contributing_references=["ref-1"],
                observation_count=3, organizational_dimension="unavailable")
    result.update(extra)
    return result


def test_deterministic_ordering_ids_and_scores():
    service = AnalystExecutiveLearningService()
    rows = service.derive("t1", [trend("stable", "stable"), trend("gap", "persistent"), trend("bad", "degrading")])
    again = service.derive("t1", [trend("bad", "degrading"), trend("gap", "persistent"), trend("stable", "stable")])
    assert [x.to_dict() for x in rows] == [x.to_dict() for x in again]
    assert [x.classification for x in rows] == ["persistent_learning_gap", "degrading_learning", "stable_learning"]
    assert all(0 <= x.relevance_score <= 1 for x in rows)


def test_tenant_isolation_and_missing_dimension_uncertainty():
    rows = AnalystExecutiveLearningService().derive("t1", [trend("mine", "improving"), trend("other", "degrading", tenant_id="t2")])
    assert len(rows) == 1 and rows[0].tenant_id == "t1"
    assert rows[0].team_focus is None


def test_classifications_and_priority_precedence():
    service = AnalystExecutiveLearningService()
    rows = service.derive("t1", [trend("a", "emerging"), trend("b", "resolved"), trend("c", "mixed"), trend("d", "improving")])
    assert [x.classification for x in rows] == ["improving_learning", "emerging_learning", "resolved_learning", "mixed_learning"]
    assert rows[0].priority == "low"


def test_summary_aggregation():
    service = AnalystExecutiveLearningService()
    signals = service.derive("t1", [trend("gap", "persistent"), trend("bad", "degrading"), trend("good", "improving")])
    summary = service.summary("t1", signals)
    assert summary.persistent_gap_count == 1
    assert summary.degrading_count == 1
    assert summary.improving_count == 1
    assert summary.advisory_only is True


def test_empty_data_is_insufficient_and_advisory():
    service = AnalystExecutiveLearningService()
    assert service.derive("t1", []) == []
    summary = service.summary("t1", [])
    assert summary.overall_posture == "insufficient_data"
    assert summary.advisory_only is True


def test_provenance_references_and_uncertainty_preserved():
    row = trend("gap", "persistent", confidence=1.2, uncertainty=["mixed_signals"])
    signal = AnalystExecutiveLearningService().derive("t1", [row])[0]
    assert signal.confidence == 1.0
    assert signal.uncertainty == ["mixed_signals"]
    assert signal.contributing_references == ["ref-1"]
    assert signal.provenance == {"source": "test"}


def test_no_upstream_mutation():
    source = [trend("gap", "persistent")]
    before = [dict(source[0])]
    AnalystExecutiveLearningService().derive("t1", source)
    assert source == before
