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

    authority = app.container.get("canonical_authority")
    authority.tenants.create("Integration Tenant", tenant_id="tenant-integration")
    authority.identities.create("integration@example.test", "Integration Analyst", actor_id="actor-integration")
    authority.memberships.add("tenant-integration", "actor-integration", "analyst")
    user = app.container.get("auth_service").register(
        "integration-analyst", "integration@example.test", "StrongPassword123!",
        tenant_id="tenant-integration", actor_id="actor-integration",
    )
    client = app.test_client()
    with client.session_transaction() as state:
        state["user_id"] = user.id
        state["actor_id"] = user.actor_id
        state["organization_id"] = user.tenant_id
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
