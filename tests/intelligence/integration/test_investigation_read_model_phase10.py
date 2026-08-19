"""Phase 10 canonical investigation read-model tests."""

from __future__ import annotations

from database.connection import DatabaseConnection
from services.intelligence.investigation.read_model import InvestigationReadModelBuilder
from services.intelligence.repository.feedback_repository import InvestigationFeedbackRepository
from services.intelligence.investigation_quality.repository import InvestigationQualityRepository
from services.intelligence.repository.intelligence_repository import IntelligenceRepository
from services.intelligence.repository.report_repository import InvestigationReportRepository


def test_read_model_is_complete_sanitized_and_deterministic(tmp_path):
    db = DatabaseConnection(tmp_path / "read-model.db")
    reports = InvestigationReportRepository(db)
    intelligence = IntelligenceRepository(db)
    quality = InvestigationQualityRepository(db)
    feedback = InvestigationFeedbackRepository(db)
    reports.save({
        "case_id": "CASE-10", "tenant_context": {"tenant_id": "tenant-a"}, "status": "completed",
        "findings": [{"finding_id": "F-2", "finding": "Second", "evidence_refs": ["E-2"]}, {"finding_id": "F-1", "finding": "First", "token": "hidden"}],
        "recommendations": [{"recommendation_id": "R-2", "recommendation": "Escalate"}],
        "evidence": [{"evidence_id": "E-2", "reference": "log-2"}], "iocs": [{"id": "IOC-1", "type": "ip", "value": "192.0.2.1"}],
        "timeline": [{"event_id": "T-2", "timestamp": "2026-01-02", "description": "Later"}, {"event_id": "T-1", "timestamp": "2026-01-01", "description": "Earlier"}],
        "metadata": {"investigation_id": "INV-10", "database_path": "secret.db"},
    })
    view = InvestigationReadModelBuilder(reports, intelligence, quality, feedback).build("CASE-10", "tenant-a").to_dict()
    assert view["investigation"]["tenant_id"] == "tenant-a"
    assert [item["finding_id"] for item in view["findings"]] == ["F-1", "F-2"]
    assert view["iocs"][0]["ioc_type"] == "ip"
    assert [item["event_id"] for item in view["timeline"]] == ["T-1", "T-2"]
    assert "token" not in str(view)
    assert "database_path" not in str(view)


def test_read_model_is_tenant_isolated_and_missing_is_explicit(tmp_path):
    db = DatabaseConnection(tmp_path / "read-model.db")
    reports = InvestigationReportRepository(db)
    reports.save({"case_id": "CASE-10", "tenant_context": {"tenant_id": "tenant-a"}})
    builder = InvestigationReadModelBuilder(reports, IntelligenceRepository(db), InvestigationQualityRepository(db), InvestigationFeedbackRepository(db))
    assert builder.build("CASE-MISSING", "tenant-a") is None
    try:
        builder.build("CASE-10", "tenant-b")
    except PermissionError as exc:
        assert str(exc) == "investigation_not_found"
    else:
        raise AssertionError("cross-tenant read-model access was not rejected")
