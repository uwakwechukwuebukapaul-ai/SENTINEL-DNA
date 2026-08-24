import uuid

import pytest

from app import create_app


@pytest.fixture
def authenticated_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "intake-api.sqlite"))
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = f"198.51.100.{int(uuid.uuid4().int % 250) + 1}"
    username = f"intake-{uuid.uuid4().hex[:10]}"
    password = "CorrectHorseBattery1!"
    assert client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@example.test", "password": password},
    ).status_code == 201
    assert client.post("/api/auth/login", json={"username": username, "password": password}).status_code == 200
    return app, client


def test_durable_intake_requires_authentication(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "unauthenticated.sqlite"))
    app = create_app()
    response = app.test_client().post(
        "/api/investigations/jobs",
        json={"case_id": "CASE-1", "alert": {"id": "event-1"}},
    )
    assert response.status_code == 401


def test_durable_intake_returns_job_without_inline_investigation(authenticated_client):
    app, client = authenticated_client
    called = []

    class Coordinator:
        def investigate(self, **_kwargs):
            called.append(True)
            raise AssertionError("durable intake must not execute investigation inline")

    app.container.register("investigation_coordinator", Coordinator())
    response = client.post(
        "/api/investigations/jobs",
        json={
            "case_id": "CASE-DURABLE-1",
            "source": "api",
            "alert": {"id": "event-durable-1", "event_type": "failed_login", "severity": "high"},
        },
    )

    assert response.status_code == 202
    body = response.get_json()
    assert body["accepted"] is True
    assert body["state"] == "QUEUED"
    assert body["job_id"]
    assert called == []
    repository = app.container.get("execution_repository")
    with repository.db.session() as connection:
        job = connection.execute(
            "SELECT job_id, state FROM investigation_jobs WHERE job_id=?",
            (body["job_id"],),
        ).fetchone()
    assert job["state"] == "QUEUED"


def test_durable_intake_replays_idempotently(authenticated_client):
    _app, client = authenticated_client
    payload = {
        "case_id": "CASE-DURABLE-2",
        "source": "api",
        "alert": {"id": "event-durable-2", "event_type": "failed_login", "severity": "high"},
    }
    first = client.post("/api/investigations/jobs", json=payload)
    second = client.post("/api/investigations/jobs", json=payload)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.get_json()["duplicate"] is True
    assert second.get_json()["job_id"] == first.get_json()["job_id"]


def test_detection_forwarding_uses_durable_intake_not_coordinator(authenticated_client):
    app, client = authenticated_client
    called = []

    class Coordinator:
        def investigate(self, **_kwargs):
            called.append(True)
            raise AssertionError("detection durable forwarding must not execute V1 inline")

    app.container.register("investigation_coordinator", Coordinator())
    csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/detection/events",
        json={
            "source": "generic",
            "event": {
                "event_type": "failed_login",
                "severity": "high",
                "case_id": "CASE-DETECTION-1",
                "hostname": "synthetic-host",
                "user": "synthetic-user",
            },
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 202
    assert response.get_json()["investigation_intake"]
    assert all(item["accepted"] for item in response.get_json()["investigation_intake"])
    assert called == []
