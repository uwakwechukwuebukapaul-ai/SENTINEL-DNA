"""End-to-end contract coverage for the investigation intelligence pipeline."""

from __future__ import annotations

import pytest

flask = pytest.importorskip("flask")

from dashboard.app import app  # noqa: E402


CASE_ID = "E2E-FAILED-AUTH-001"
ALERT = {
    "case_id": CASE_ID,
    "title": "Suspicious authentication activity",
    "severity": "HIGH",
    "description": "Multiple failed logins from a suspicious external IP.",
}
ARTIFACTS = [
    {
        "type": "LOG",
        "data": (
            "Multiple failed login attempts from 185.220.101.44. "
            "User admin authentication failure. Suspicious remote access attempt."
        ),
    }
]


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_end_to_end_investigation_contract(client):
    response = client.post(
        "/api/investigations",
        json={"case_id": CASE_ID, "alert": ALERT, "artifacts": ARTIFACTS},
    )

    assert response.status_code == 200
    started = response.get_json()
    assert started["case_id"] == CASE_ID
    assert started["risk"]["score"] == 65
    assert started["confidence"] == pytest.approx(0.95)
    assert "T1110" in started["mitre"]
    assert started["findings"]
    assert started["recommendations"]
    assert started["attack_story"]

    investigation = client.get(f"/api/investigations/{CASE_ID}")
    assert investigation.status_code == 200
    data = investigation.get_json()
    assert data["intelligence"]["risk_score"] == 65
    assert data["timeline"]
    assert data["report"]["case_id"] == CASE_ID

    report = client.get(f"/api/investigations/{CASE_ID}/report")
    assert report.status_code == 200
    report_data = report.get_json()
    assert report_data["risk"]["score"] == 65
    assert report_data["mitre"] == ["T1110"]
    assert report_data["attack_story"]
    assert report_data["recommendations"]

    timeline = client.get(f"/api/investigations/{CASE_ID}/timeline")
    assert timeline.status_code == 200
    events = timeline.get_json()["timeline"]
    descriptions = [event["description"] for event in events]
    assert descriptions == [
        "Alert received",
        "Authentication failures detected",
        "Suspicious external IP identified",
        "MITRE T1110 mapped",
        "Recommended response generated",
    ]
