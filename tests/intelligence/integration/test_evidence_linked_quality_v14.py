from types import SimpleNamespace

import pytest
from flask import Flask, g

from services.api.investigations.routes import investigations_api
from services.intelligence.feedback.analytics import FeedbackAnalyticsService
from services.intelligence.investigation.analyst_feedback import AnalystFeedback


def feedback(decision, *, finding_id=None, recommendation_id=None, created_at="2026-08-19T10:00:00+00:00"):
    return AnalystFeedback(
        investigation_id="INV-1",
        case_id="CASE-1",
        decision=decision,
        analyst_id="actor-a",
        finding_id=finding_id,
        recommendation_id=recommendation_id,
        created_at=created_at,
        tenant_id="tenant-a",
    )


def report():
    return {
        "case_id": "CASE-1",
        "metadata": {"investigation_id": "INV-1", "tenant_id": "tenant-a"},
        "evidence": [{"evidence_id": "EV-2", "evidence_type": "email"}, {"evidence_id": "EV-1", "evidence_type": "log"}],
        "findings": [{"finding_id": "F-1", "finding_type": "credential_abuse"}],
        "recommendations": [{"recommendation_id": "R-1", "recommendation_type": "containment"}],
    }


def test_evidence_linked_quality_is_deterministic_and_advisory():
    records = [
        feedback("accepted", finding_id="F-1", recommendation_id="R-1"),
        feedback("rejected", finding_id="F-1", recommendation_id="R-1", created_at="2026-08-19T11:00:00+00:00"),
        feedback("modified", created_at="2026-08-19T12:00:00+00:00"),
    ]

    result = FeedbackAnalyticsService(object()).evidence_linked_quality("tenant-a", report(), records)

    assert result["case_id"] == "CASE-1"
    assert result["investigation_id"] == "INV-1"
    assert result["feedback_count"] == 3
    assert result["advisory"] is True
    assert [item["evidence_id"] for item in result["evidence"]] == ["EV-2", "EV-1"]
    assert result["evidence"][0]["feedback_count"] == 3
    assert result["findings"][0]["feedback_count"] == 3
    assert result["findings"][0]["acceptance_rate"] == 0.333333
    assert result["recommendations"][0]["rejection_rate"] == 0.333333
    assert result["findings"][0]["insufficient_feedback_volume"] is False
    assert result["evidence"][0]["association_basis"] == "case_feedback"


def test_evidence_linked_quality_marks_small_samples_and_supports_filters():
    result = FeedbackAnalyticsService(object()).evidence_linked_quality(
        "tenant-a", report(), [feedback("accepted", finding_id="F-1")], finding_type="credential_abuse", limit=1
    )

    assert len(result["findings"]) == 1
    assert result["findings"][0]["insufficient_feedback_volume"] is True
    assert result["findings"][0]["feedback_count"] == 1
    assert len(result["evidence"]) == 1
    assert all(item["feedback_count"] == 1 for item in result["evidence"])
    assert all(item["insufficient_feedback_volume"] is True for item in result["evidence"])

    with pytest.raises(ValueError, match="invalid_limit"):
        FeedbackAnalyticsService(object()).evidence_linked_quality("tenant-a", report(), [], limit=101)
    with pytest.raises(ValueError, match="invalid_decision"):
        FeedbackAnalyticsService(object()).evidence_linked_quality("tenant-a", report(), [], decision="unknown")


class QualityCoordinator:
    def get_evidence_linked_quality(self, case_id, tenant_id, **filters):
        assert case_id == "CASE-1"
        assert tenant_id == "tenant-a"
        return {"case_id": case_id, "feedback_count": 0, "evidence": [], "findings": [], "recommendations": [], **filters}


def api_app():
    app = Flask(__name__)
    app.testing = True
    app.secret_key = "test"
    app.container = SimpleNamespace(get=lambda name: QualityCoordinator())

    @app.before_request
    def security_context():
        g.security_context = SimpleNamespace(
            tenant_id="tenant-a",
            actor_id="actor-a",
            user_id="actor-a",
            roles=("analyst",),
            correlation_id="test-quality",
            tenant_context_valid=True,
        )

    app.register_blueprint(investigations_api)
    return app


def test_quality_api_is_read_only_tenant_scoped_and_bounded():
    client = api_app().test_client()
    response = client.get("/api/investigations/CASE-1/quality/evidence?limit=2&decision=accepted")
    assert response.status_code == 200
    assert "tenant_id" not in response.get_json()
    assert response.get_json()["limit"] == 2
    assert client.get("/api/investigations/CASE-1/quality/evidence?tenant_id=tenant-b").status_code == 400
    assert client.get("/api/investigations/CASE-1/quality/evidence?limit=not-an-int").status_code == 400
    assert client.get("/api/investigations/CASE-1/quality/evidence?unknown=value").status_code == 400
    assert client.post("/api/investigations/CASE-1/quality/evidence").status_code == 405
