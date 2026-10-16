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
from services.auth.providers import TestEmailProvider
from tests.security.conftest import register_and_login_analyst


def create_client(monkeypatch, db_path):

    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(db_path))

    app = create_app()

    app.testing = True
    app.config["EMAIL_PROVIDER"] = TestEmailProvider()

    client = app.test_client()
    register_and_login_analyst(client, "e2e-investigator", "e2e-investigator@example.test")
    return client



def test_end_to_end_investigation_execution(monkeypatch, tmp_path):

    client = create_client(monkeypatch, tmp_path / "end-to-end.sqlite")


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



def test_empty_investigation_request(monkeypatch, tmp_path):

    client = create_client(monkeypatch, tmp_path / "empty-investigation.sqlite")


    response = client.post(
        "/api/investigations/run",
        json={},
    )


    assert response.status_code == 200


    data = response.get_json()


    assert data is not None
