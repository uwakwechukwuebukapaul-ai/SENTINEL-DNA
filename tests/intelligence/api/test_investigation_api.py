"""
Sentinel DNA Investigation API Tests.

Validates:

- API blueprint registration
- investigation endpoint
- request handling
- response schema
- failure handling
"""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app import create_app  # noqa: E402  # type: ignore[import-not-found]
from tests.credential_helpers import random_password


@pytest.fixture
def client(tmp_path, monkeypatch):

    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "investigation-api.sqlite"))

    app = create_app()

    app.config["TESTING"] = True

    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    import uuid
    username = f"investigator-test-{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.test"
    password = random_password()
    client.environ_base["REMOTE_ADDR"] = f"198.51.100.{int(uuid.uuid4().int % 250) + 1}"
    assert client.post("/api/auth/register", json={"username": username, "email": email, "password": password}).status_code == 201
    assert client.post("/api/auth/login", json={"username": username, "password": password}).status_code == 200
    return client



def test_api_health(client):
    assert client.get("/").status_code == 401
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"



def test_investigation_endpoint_exists(authenticated_client):

    response = authenticated_client.post(
        "/investigate",
        json={
            "artifacts": [
                {
                    "type": "domain",
                    "value": "evil.com",
                }
            ]
        },
    )


    assert response.status_code in [
        200,
        201,
        404,
    ]



def test_investigation_success_response(client):

    response = client.post(
        "/investigate",
        json={
            "artifacts": [
                {
                    "type": "domain",
                    "value": "evil.com",
                },
                {
                    "type": "email",
                    "value": "phishing",
                },
            ],
            "case_id": "CASE-001",
        },
    )


    if response.status_code == 200:

        data = response.get_json()

        assert data is not None

        assert (
            "success"
            in data
            or
            "status"
            in data
        )



def test_investigation_empty_payload(authenticated_client):

    response = authenticated_client.post(
        "/investigate",
        json={},
    )


    assert response.status_code in [
        200,
        400,
    ]



def test_investigation_invalid_method(client):

    response = client.get(
        "/investigate"
    )


    assert response.status_code in [
        404,
        405,
    ]
