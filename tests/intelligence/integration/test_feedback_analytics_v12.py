"""Focused V1.2 feedback analytics tests."""

from __future__ import annotations

import pytest

from services.intelligence.feedback.analytics import FeedbackAnalyticsService
from services.intelligence.investigation.analyst_feedback import AnalystFeedback


class Repository:
    def __init__(self, records):
        self.records = list(records)

    def list_for_tenant(self, tenant_id, **filters):
        values = [item for item in self.records if item.tenant_id == tenant_id]
        if filters.get("case_id"):
            values = [item for item in values if item.case_id == filters["case_id"]]
        if filters.get("investigation_id"):
            values = [item for item in values if item.investigation_id == filters["investigation_id"]]
        if filters.get("start"):
            values = [item for item in values if item.created_at >= filters["start"]]
        if filters.get("end"):
            values = [item for item in values if item.created_at <= filters["end"]]
        return values


def feedback(index, decision, tenant="tenant-a", created_at="2026-08-19T10:00:00+00:00", case_id="case-1", investigation_id="inv-1"):
    return AnalystFeedback(
        feedback_id=f"FB-{index}", investigation_id=investigation_id, case_id=case_id,
        decision=decision, analyst_id=f"actor-{index}", tenant_id=tenant, created_at=created_at,
    )


def test_analytics_counts_rates_and_groups_are_deterministic():
    service = FeedbackAnalyticsService(Repository([
        feedback(1, "accepted"), feedback(2, "rejected"), feedback(3, "false_positive"),
        feedback(4, "modified", case_id="case-2", investigation_id="inv-2"),
        feedback(5, "escalated", tenant="tenant-b"),
    ]))
    result = service.summarize("tenant-a").to_dict()
    assert result["total_feedback_events"] == 4
    assert result["counts"] == {"accepted": 1, "rejected": 1, "modified": 1, "false_positive": 1, "escalated": 0}
    assert result["rates"]["accepted_rate"] == 0.25
    assert result["rates"]["escalated_rate"] == 0.0
    assert [item["id"] for item in result["by_case"]] == ["case-1", "case-2"]
    assert result["advisory_only"] is True
    assert result["signal_basis"] == "analyst_feedback_events"


def test_empty_and_time_window_analytics_are_safe():
    service = FeedbackAnalyticsService(Repository([feedback(1, "accepted", created_at="2026-08-19T10:00:00+00:00")]))
    empty = service.summarize("tenant-a", start="2026-08-20T00:00:00Z").to_dict()
    assert empty["total_feedback_events"] == 0
    assert all(value == 0.0 for value in empty["rates"].values())
    included = service.summarize("tenant-a", start="2026-08-19T10:00:00Z", end="2026-08-19T10:00:00Z")
    assert included.total_feedback_events == 1


def test_invalid_filters_are_rejected_without_source_mutation():
    records = [feedback(1, "accepted")]
    service = FeedbackAnalyticsService(Repository(records))
    with pytest.raises(ValueError, match="invalid_time_range"):
        service.summarize("tenant-a", start="2026-08-20T00:00:00Z", end="2026-08-19T00:00:00Z")
    with pytest.raises(ValueError, match="invalid_bucket"):
        service.summarize("tenant-a", bucket="month")
    assert records[0].decision == "accepted"


def test_authenticated_analytics_api_is_tenant_scoped_and_read_only(canonical_authenticated_client):
    case_id = "V12-ANALYTICS-001"
    created = canonical_authenticated_client.post(
        "/api/investigations",
        json={"case_id": case_id, "alert": {"title": "Analytics test"}, "artifacts": [{"type": "log", "data": "event"}]},
    )
    assert created.status_code == 200
    for decision in ("accepted", "false_positive", "escalated"):
        response = canonical_authenticated_client.post(
            f"/api/investigations/{case_id}/feedback", json={"decision": decision},
        )
        assert response.status_code == 201
    response = canonical_authenticated_client.get("/api/investigations/feedback/analytics")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total_feedback_events"] == 3
    assert payload["counts"]["false_positive"] == 1
    assert payload["rates"]["accepted_rate"] == pytest.approx(1 / 3, abs=1e-6)
    assert "tenant_id" not in payload

    invalid = canonical_authenticated_client.get("/api/investigations/feedback/analytics?granularity=monthly")
    assert invalid.status_code == 400
