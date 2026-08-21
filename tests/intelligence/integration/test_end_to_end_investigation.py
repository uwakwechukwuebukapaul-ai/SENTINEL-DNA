"""
Sentinel DNA End-to-End Investigation Test.

Validates complete API investigation flow.
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from app import create_app


def create_client():

    app = create_app()

    app.testing = True

    client = app.test_client()
    client.post("/api/auth/register", json={"username": "e2e-investigator", "email": "e2e-investigator@example.test", "password": "CorrectHorseBattery1!"})
    client.post("/api/auth/login", json={"username": "e2e-investigator", "password": "CorrectHorseBattery1!"})
    return client



def test_end_to_end_investigation_execution():

    client = create_client()


    response = client.post(
        "/api/investigations/run",
        json={
            "case_id": "CASE-E2E-001",
            "artifacts": [
                {
                    "type": "domain",
                    "value": "evil.com",
                },
                {
                    "type": "email",
                    "value": "credential phishing",
                },
            ],
        },
    )


    assert response.status_code == 200


    data = response.get_json()


    assert data is not None


    assert (
        "status"
        in data
        or
        "success"
        in data
    )



def test_empty_investigation_request():

    client = create_client()


    response = client.post(
        "/api/investigations/run",
        json={},
    )


    assert response.status_code == 200


    data = response.get_json()


    assert data is not None
