"""Phase 9 durable analyst outcome boundary tests."""

from __future__ import annotations

import pytest

from database.connection import DatabaseConnection
from services.intelligence.investigation.analyst_feedback_service import AnalystFeedbackService
from services.intelligence.repository.feedback_repository import InvestigationFeedbackRepository


def _service(path):
    database = DatabaseConnection(path)
    repository = InvestigationFeedbackRepository(database)
    return database, repository, AnalystFeedbackService(repository)


def _report():
    return {
        "metadata": {"investigation_id": "INV-9"},
        "findings": [{"finding_id": "F-1"}],
        "recommendations": [{"recommendation_id": "R-1"}],
        "quality_assessment": {"evidence_refs": ["E-1"], "artifact_refs": ["A-1"]},
        "evidence": [{"evidence_id": "E-2"}],
    }


def test_service_records_server_authored_identity_and_provenance(tmp_path):
    _, repository, service = _service(tmp_path / "feedback.db")
    value = service.record("INV-9", "CASE-9", "tenant-a", "analyst-a", {"decision": "accepted", "finding_id": "F-1", "recommendation_id": "R-1"}, _report())
    assert value.tenant_id == "tenant-a"
    assert value.analyst_id == "analyst-a"
    assert value.evidence_refs == ["E-1", "E-2"]
    assert value.artifact_refs == ["A-1"]
    assert repository.list_for_investigation("tenant-a", "INV-9")[0] == value


def test_service_rejects_identity_fields_and_unknown_references(tmp_path):
    _, _, service = _service(tmp_path / "feedback.db")
    with pytest.raises(ValueError, match="invalid_feedback_fields"):
        service.record("INV-9", "CASE-9", "tenant-a", "analyst-a", {"decision": "accepted", "tenant_id": "forged"}, _report())
    with pytest.raises(ValueError, match="finding_not_found"):
        service.record("INV-9", "CASE-9", "tenant-a", "analyst-a", {"decision": "accepted", "finding_id": "forged"}, _report())


def test_feedback_survives_database_restart_and_remains_append_only(tmp_path):
    path = tmp_path / "feedback.db"
    database, repository, service = _service(path)
    first = service.record("INV-9", "CASE-9", "tenant-a", "analyst-a", {"decision": "accepted"}, _report())
    service.record("INV-9", "CASE-9", "tenant-a", "analyst-a", {"decision": "modified", "reason": "Adjusted scope."}, _report())
    del database, repository, service
    _, restarted_repository, _ = _service(path)
    history = restarted_repository.list_for_investigation("tenant-a", "INV-9")
    assert [item.decision for item in history] == ["accepted", "modified"]
    assert history[0].feedback_id == first.feedback_id
    assert restarted_repository.list_for_investigation("tenant-b", "INV-9") == []


def test_sensitive_payload_is_rejected_and_not_persisted(tmp_path):
    path = tmp_path / "feedback.db"
    database, repository, service = _service(path)
    with pytest.raises(ValueError, match="invalid_feedback_fields"):
        service.record("INV-9", "CASE-9", "tenant-a", "analyst-a", {"decision": "accepted", "metadata": {"token": "secret"}}, _report())
    with database.session() as connection:
        row = connection.execute("SELECT metadata_json FROM investigation_feedback").fetchone()
    assert row is None
