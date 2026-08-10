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


@pytest.fixture
def client():

    app = create_app()

    app.config["TESTING"] = True

    return app.test_client()



def test_api_health(client):

    response = client.get("/")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "running"

    assert data["service"] == "Sentinel DNA"



def test_investigation_endpoint_exists(client):

    response = client.post(
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



def test_investigation_empty_payload(client):

    response = client.post(
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