"""Focused V1.1 analyst outcome and feedback boundary tests."""

from __future__ import annotations

import pytest

from database.connection import database
from services.intelligence.investigation.analyst_feedback import AnalystFeedback
from services.intelligence.repository.feedback_repository import InvestigationFeedbackRepository


@pytest.mark.parametrize("decision", ["accepted", "rejected", "modified", "false_positive", "escalated"])
def test_feedback_contract_accepts_only_supported_decisions(decision):
    value = AnalystFeedback(
        investigation_id="INV-1", case_id="CASE-1", decision=decision,
        analyst_id="actor-1", tenant_id="tenant-1", reason="Reviewed evidence.",
    )
    assert value.to_dict()["decision"] == decision


def test_feedback_contract_rejects_unknown_decision_and_long_reason():
    with pytest.raises(ValueError, match="invalid_decision"):
        AnalystFeedback(investigation_id="INV-1", case_id="CASE-1", decision="approve", analyst_id="actor-1", tenant_id="tenant-1")
    with pytest.raises(ValueError, match="reason_too_long"):
        AnalystFeedback(investigation_id="INV-1", case_id="CASE-1", decision="accepted", analyst_id="actor-1", tenant_id="tenant-1", reason="x" * 2001)


def test_feedback_repository_preserves_append_only_history_and_identity():
    repository = InvestigationFeedbackRepository(database)
    first = AnalystFeedback(investigation_id="INV-1", case_id="CASE-1", decision="accepted", analyst_id="actor-1", tenant_id="tenant-1")
    second = AnalystFeedback(investigation_id="INV-1", case_id="CASE-1", decision="modified", analyst_id="actor-1", tenant_id="tenant-1")
    repository.save(first)
    repository.save(second)
    values = repository.list_for_investigation("tenant-1", "INV-1")
    assert [item.decision for item in values] == ["accepted", "modified"]
    assert [item.analyst_id for item in values] == ["actor-1", "actor-1"]
    assert repository.list_for_investigation("tenant-2", "INV-1") == []


def test_authenticated_feedback_does_not_overwrite_ai_report(canonical_authenticated_client):
    case_id = "V11-FEEDBACK-001"
    investigation = canonical_authenticated_client.post(
        "/api/investigations",
        json={"case_id": case_id, "alert": {"title": "Suspicious login"}, "artifacts": [{"type": "log", "data": "failed login"}]},
    )
    assert investigation.status_code == 200
    before = canonical_authenticated_client.get(f"/api/investigations/{case_id}/report").get_json()

    response = canonical_authenticated_client.post(
        f"/api/investigations/{case_id}/feedback",
        json={"decision": "false_positive", "reason": "Known internal simulation.", "analyst_id": "forged"},
    )
    assert response.status_code == 400

    response = canonical_authenticated_client.post(
        f"/api/investigations/{case_id}/feedback",
        json={"decision": "false_positive", "reason": "Known internal simulation."},
    )
    assert response.status_code == 201
    feedback = response.get_json()["feedback"]
    assert feedback["analyst_id"] == "actor-a"
    assert feedback["case_id"] == case_id

    after = canonical_authenticated_client.get(f"/api/investigations/{case_id}/report").get_json()
    assert after == before
    history = canonical_authenticated_client.get(f"/api/investigations/{case_id}/feedback")
    assert history.status_code == 200
    assert history.get_json()["feedback"][0]["decision"] == "false_positive"
