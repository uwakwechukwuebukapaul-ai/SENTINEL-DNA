from services.intelligence.command_center.maturity_service import OrganizationalMaturityService


def learning(kind, classification, tenant_id="t1", confidence=.8):
    return {"tenant_id": tenant_id, "learning_type": kind, "title": kind, "classification": classification, "confidence": confidence, "uncertainty": [], "investigation_count": 3, "contributing_investigation_ids": ["i1"], "contributing_feedback_ids": ["f1"], "contributing_learning_ids": ["l1"]}


def test_deterministic_bounded_maturity_and_baseline():
    service = OrganizationalMaturityService()
    value = service.derive("t1", organizational_learning=[learning("evidence_gap", "improving")], trends=[{"tenant_id": "t1", "classification": "improving"}], historical_scores=[60, 64])
    again = service.derive("t1", organizational_learning=[learning("evidence_gap", "improving")], trends=[{"tenant_id": "t1", "classification": "improving"}], historical_scores=[60, 64])
    assert value.to_dict() == again.to_dict()
    assert 0 <= value.maturity_score <= 100
    assert value.historical_baseline == 62
    assert value.benchmark_status == "above_historical_baseline"
    assert value.advisory_only is True


def test_insufficient_data_and_peer_unavailable():
    value = OrganizationalMaturityService().derive("t1", organizational_learning=[])
    assert value.classification == "insufficient_data"
    assert value.maturity_level == "insufficient_data"
    assert value.peer_benchmark_status == "unavailable"
    assert value.uncertainty


def test_tenant_isolation_and_recommendation():
    value = OrganizationalMaturityService().derive("t1", organizational_learning=[learning("gap", "degrading", tenant_id="t2")])
    assert value.classification == "insufficient_data"
    value = OrganizationalMaturityService().derive("t1", organizational_learning=[learning("gap", "persistent_pattern")])
    assert value.signals[0]["signal_type"] == "persistent_learning_gap"
    assert value.recommendations


def test_mixed_trend_and_confidence_uncertainty():
    value = OrganizationalMaturityService().derive("t1", organizational_learning=[learning("gap", "mixed", confidence=.5)], trends=[{"tenant_id": "t1", "classification": "mixed"}])
    assert value.trend == "mixed"
    assert value.confidence == .5
