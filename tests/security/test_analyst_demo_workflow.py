from unittest.mock import patch

import pytest


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "workflow.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    from app import create_app

    app = create_app()
    app.config.update(TESTING=True, DEMO_DATA_ENABLED=True)
    return app


def login(client, username="workflow-user", email="workflow@example.test"):
    assert client.post("/api/auth/register", json={"username": username, "email": email, "password": "CorrectHorseBattery1!"}).status_code == 201
    assert client.post("/api/auth/login", json={"username": username, "password": "CorrectHorseBattery1!"}).status_code == 200


def test_workspace_provisions_one_tenant_scoped_synthetic_case(application):
    client = application.test_client()
    login(client)

    response = client.get("/workspace/")
    assert response.status_code == 200
    assert b"DEMO-PS-" in response.data
    assert b"Synthetic" in response.data
    dashboard = client.get("/")
    assert b"Threat level" in dashboard.data
    assert b"Risk distribution" in dashboard.data
    assert b"Confidence distribution" in dashboard.data
    assert b"MITRE ATT&amp;CK coverage" in dashboard.data
    assert b"Recent investigation activity" in dashboard.data
    assert b"Tenant-scoped investigations" in response.data
    assert b"MITRE ATT&CK coverage" in response.data

    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    scenario = application.container.require("analyst_demo_scenario")
    seeded = scenario.ensure_for_tenant(tenant_id)
    assert seeded["metadata"]["synthetic"] is True
    assert seeded["metadata"]["tenant_id"] == tenant_id
    assert scenario.ensure_for_tenant(tenant_id)["case_id"] == seeded["case_id"]
    snapshot = application.container.require("investigation_coordinator").get_workspace_snapshot(tenant_id)
    assert snapshot["overview"]["evidence_collected"] == 3
    assert snapshot["overview"]["ioc_intelligence"] == 1
    assert snapshot["visualizations"]["severity_distribution"] == [{"label": "High", "count": 1}]
    assert snapshot["visualizations"]["ioc_reputation_distribution"] == [{"label": "Not Queried", "count": 1}]
    assert snapshot["visualizations"]["confidence_distribution"]
    assert snapshot["visualizations"]["activity"]


def test_start_uses_canonical_coordinator_and_report(application):
    client = application.test_client()
    login(client, "start-user", "start@example.test")
    client.get("/workspace/")
    case_id = next(iter(application.container.require("investigation_coordinator").get_workspace_snapshot("tenant-1")["investigations"]), {}).get("case_id")
    if not case_id:
        with client.session_transaction() as state:
            case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(state["organization_id"])

    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    coordinator = application.container.require("investigation_coordinator")
    original = coordinator.investigate
    with patch.object(coordinator, "investigate", wraps=original) as investigated:
        response = client.post(f"/workspace/investigation/{case_id}/start", headers={"X-CSRF-Token": token})

    assert response.status_code == 302
    investigated.assert_called_once()
    assert investigated.call_args.kwargs["tenant_id"].startswith("tenant-")
    assert investigated.call_args.kwargs["actor_id"]
    assert investigated.call_args.kwargs["evidence"]
    assert investigated.call_args.kwargs["iocs"]
    detail = client.get(f"/workspace/investigation/{case_id}")
    report = client.get(f"/workspace/investigation/{case_id}/report")
    assert detail.status_code == 200
    assert report.status_code == 200
    assert b"Evidence" in detail.data
    assert b"IOC intelligence" in detail.data
    assert b"Evidence summary" in report.data
    assert b"synthetic_demo" in report.data


def test_disabled_demo_mode_preserves_honest_empty_states(application):
    application.config["DEMO_DATA_ENABLED"] = False
    client = application.test_client()
    login(client, "empty-user", "empty@example.test")
    assert b"No investigations are available" in client.get("/").data
    assert b"No active investigations" in client.get("/workspace/").data


def test_demo_case_is_not_readable_across_tenants(application):
    first = application.test_client()
    login(first, "first-user", "first@example.test")
    first.get("/workspace/")
    with first.session_transaction() as state:
        case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(state["organization_id"])

    second = application.test_client()
    login(second, "second-user", "second@example.test")
    assert second.get(f"/workspace/investigation/{case_id}").status_code == 404
    assert second.get(f"/workspace/investigation/{case_id}/report").status_code == 404
