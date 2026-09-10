from __future__ import annotations

import pytest

from database.backend import SQLiteBackend
from services.intelligence.investigation.analyst_feedback_service import AnalystFeedbackService
from services.intelligence.repository.feedback_repository import InvestigationFeedbackRepository


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))


def payload(**overrides):
    value = {
        "decision": "accepted",
        "helpful_rating": 5,
        "confidence_rating": 4,
        "estimated_time_saved": 30,
        "analyst_comments": "Investigation reduced from 45 minutes to 15 minutes.",
    }
    value.update(overrides)
    return value


def test_pilot_feedback_is_persisted_with_server_attribution_and_audit(tmp_path):
    database = SQLiteBackend(tmp_path / "feedback.sqlite")
    repository = InvestigationFeedbackRepository(database)
    audit = Audit()
    service = AnalystFeedbackService(repository, audit)

    feedback = service.record(
        investigation_id="INV-1",
        case_id="CASE-1",
        tenant_id="tenant-a",
        analyst_id="analyst-a",
        payload=payload(),
    )

    assert feedback.feedback_id.startswith("FB-")
    assert feedback.tenant_id == "tenant-a"
    assert feedback.analyst_id == "analyst-a"
    assert feedback.helpful_rating == 5
    assert feedback.confidence_rating == 4
    assert feedback.estimated_time_saved == 30
    assert feedback.analyst_comments.startswith("Investigation reduced")
    assert feedback.created_at
    assert audit.events[0][0] == "INVESTIGATION_FEEDBACK_RECORDED"
    assert repository.list_for_investigation("tenant-a", "INV-1")[0].to_dict() == feedback.to_dict()
    assert repository.list_for_investigation("tenant-b", "INV-1") == []


def test_pilot_feedback_validation_is_fail_closed(tmp_path):
    service = AnalystFeedbackService(
        InvestigationFeedbackRepository(SQLiteBackend(tmp_path / "feedback.sqlite"))
    )
    with pytest.raises(ValueError, match="complete_pilot_feedback_required"):
        service.record(
            investigation_id="INV-1",
            case_id="CASE-1",
            tenant_id="tenant-a",
            analyst_id="analyst-a",
            payload={"decision": "accepted", "helpful_rating": 5},
        )
    with pytest.raises(ValueError, match="invalid_helpful_rating"):
        service.record(
            investigation_id="INV-1",
            case_id="CASE-1",
            tenant_id="tenant-a",
            analyst_id="analyst-a",
            payload=payload(helpful_rating=6),
        )
    with pytest.raises(ValueError, match="invalid_feedback_fields"):
        service.record(
            investigation_id="INV-1",
            case_id="CASE-1",
            tenant_id="tenant-a",
            analyst_id="analyst-a",
            payload=payload(created_at="2000-01-01T00:00:00+00:00"),
        )


def test_feedback_ordering_is_portable_and_deterministic(tmp_path):
    database = SQLiteBackend(tmp_path / "feedback.sqlite")
    repository = InvestigationFeedbackRepository(database)
    service = AnalystFeedbackService(repository)
    for comment in ("first", "second"):
        service.record(
            investigation_id="INV-1",
            case_id="CASE-1",
            tenant_id="tenant-a",
            analyst_id="analyst-a",
            payload=payload(analyst_comments=comment),
        )

    assert [item.analyst_comments for item in repository.list_for_tenant("tenant-a")] == [
        "first",
        "second",
    ]


def test_feedback_record_has_no_update_api_and_timestamp_is_server_authored(tmp_path):
    database = SQLiteBackend(tmp_path / "feedback.sqlite")
    repository = InvestigationFeedbackRepository(database)
    feedback = AnalystFeedbackService(repository).record(
        investigation_id="INV-1",
        case_id="CASE-1",
        tenant_id="tenant-a",
        analyst_id="analyst-a",
        payload=payload(),
    )
    assert feedback.created_at
    with pytest.raises(ValueError, match="invalid_feedback_fields"):
        AnalystFeedbackService(repository).record(
            investigation_id="INV-1",
            case_id="CASE-1",
            tenant_id="tenant-a",
            analyst_id="analyst-a",
            payload=payload(created_at="2000-01-01T00:00:00+00:00"),
        )
    assert repository.list_for_tenant("tenant-a")[0].feedback_id == feedback.feedback_id
