from services.intelligence.command_center.maturity_reporting_service import MaturityReportingService


class Current:
    tenant_id = "t1"; maturity_score = 78; maturity_level = "Advanced"; confidence = .7; evidence_strength = "strong"; uncertainty = []; dimensions = []


def test_deterministic_report_and_insufficient_history():
    service = MaturityReportingService()
    assert service.derive("t1", Current(), []).to_dict() == service.derive("t1", Current(), []).to_dict()
    report = service.derive("t1", Current(), [])
    assert report.trajectory == "insufficient_data" and report.advisory_only is True
    assert report.peer_benchmark_status == "unavailable"


def test_improving_transition_and_delta():
    history = [{"tenant_id": "t1", "timestamp": "2026-01-01", "score": 60, "level": "Developing", "contributing_references": ["r1"]}, {"tenant_id": "t1", "timestamp": "2026-02-01", "score": 65, "level": "Developing"}]
    report = MaturityReportingService().derive("t1", Current(), history)
    assert report.score_delta == 13
    assert report.trajectory == "improving"
    assert report.maturity_transition == "maturity_transition"
    assert report.temporal_span == "2026-01-01..2026-02-01"
    assert report.contributing_references == ["r1"]


def test_tenant_isolation():
    history = [{"tenant_id": "t2", "timestamp": "2026-01-01", "score": 90}, {"tenant_id": "t2", "timestamp": "2026-02-01", "score": 80}]
    assert MaturityReportingService().derive("t1", Current(), history).trajectory == "insufficient_data"
