"""End-to-end contract coverage for the investigation intelligence pipeline."""

from __future__ import annotations

import pytest

flask = pytest.importorskip("flask")

from app import create_app  # noqa: E402


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
def client(tmp_path, monkeypatch):
    import uuid
    from database.connection import database
    from services.auth.auth_service import AuthService

    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    original_path = database.database_path
    database.database_path = str(tmp_path / "contract.sqlite")
    app = create_app()
    app.config["TESTING"] = True
    auth = app.container.get("auth_service")
    app.container.register("auth_service", AuthService(database))
    client = app.test_client()
    # Keep the production limiter active while isolating this fixture's
    # bucket from earlier test processes and shared local SQLite state.
    client.environ_base["REMOTE_ADDR"] = f"198.51.100.{int(uuid.uuid4().int % 250) + 1}"
    username = f"contract-{uuid.uuid4().hex[:12]}"
    email = f"{username}@example.test"
    password = "CorrectHorseBattery1!"
    assert client.post("/api/auth/register", json={"username": username, "email": email, "password": password}).status_code == 201
    assert client.post("/api/auth/login", json={"username": username, "password": password}).status_code == 200
    try:
        yield client
    finally:
        app.container.register("auth_service", auth)
        database.database_path = original_path


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
