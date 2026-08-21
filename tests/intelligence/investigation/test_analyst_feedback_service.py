from __future__ import annotations

import pytest

from services.intelligence.investigation.analyst_feedback_service import (
    AnalystFeedbackService,
)


class Repository:
    def __init__(self):
        self.saved = []

    def save(self, feedback):
        self.saved.append(feedback)
        return feedback


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))


def test_feedback_service_server_authors_identity_and_audits_event():
    repository = Repository()
    audit = Audit()
    feedback = AnalystFeedbackService(repository, audit).record(
        investigation_id="INV-1",
        case_id="CASE-1",
        tenant_id="tenant-a",
        analyst_id="actor-a",
        payload={"decision": "accepted", "reason": "Reviewed."},
    )

    assert feedback.tenant_id == "tenant-a"
    assert feedback.analyst_id == "actor-a"
    assert repository.saved == [feedback]
    assert audit.events[0][0] == "INVESTIGATION_FEEDBACK_RECORDED"
    assert audit.events[0][1]["details"]["actor_id"] == "actor-a"


def test_feedback_service_rejects_client_controlled_identity_and_unknown_fields():
    service = AnalystFeedbackService(Repository())

    with pytest.raises(ValueError, match="invalid_feedback_fields"):
        service.record(
            investigation_id="INV-1",
            case_id="CASE-1",
            tenant_id="tenant-a",
            analyst_id="actor-a",
            payload={"decision": "accepted", "analyst_id": "forged"},
        )
