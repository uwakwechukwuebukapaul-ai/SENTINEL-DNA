from unittest.mock import patch

import pytest
import dashboard.app as dashboard_app
from tests.security.conftest import register_and_login_analyst


@pytest.fixture
def application(canonical_application):
    canonical_application.config["DEMO_DATA_ENABLED"] = True
    return canonical_application


def test_workspace_provisions_one_tenant_scoped_synthetic_case(application):
    client = application.test_client()
    register_and_login_analyst(client, "workflow-user", "workflow@example.test")

    response = client.get("/workspace/")
    assert response.status_code == 200
    assert b"DEMO-PS-" in response.data
    assert b"Synthetic" in response.data
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


def test_workspace_slash_forms_share_authorization_and_queue(canonical_application):
    client = canonical_application.test_client()
    assert client.get("/workspace").status_code == 401
    assert client.get("/workspace/").status_code == 401

    canonical_application.config["DEMO_DATA_ENABLED"] = True
    register_and_login_analyst(client, "slash-user", "slash@example.test")
    without_slash = client.get("/workspace")
    with_slash = client.get("/workspace/")
    assert without_slash.status_code == with_slash.status_code == 200
    assert b"Tenant-scoped investigations" in without_slash.data
    assert b"Tenant-scoped investigations" in with_slash.data


def test_demo_data_setting_defaults_and_override():
    assert dashboard_app._demo_data_enabled("development", None) is True
    assert dashboard_app._demo_data_enabled("testing", None) is True
    assert dashboard_app._demo_data_enabled("production", None) is False
    assert dashboard_app._demo_data_enabled("development", "0") is False
    assert dashboard_app._demo_data_enabled("production", "1") is True


def test_start_uses_canonical_coordinator_and_report(application):
    client = application.test_client()
    register_and_login_analyst(client, "start-user", "start@example.test")
    client.get("/workspace/")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(tenant_id)

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
    executions = coordinator.execution_repository.list_for_tenant(tenant_id, investigation_id=case_id)
    assert executions
    assert executions[0]["status"].lower() == "completed"
    assert executions[0]["evidence_references"]
    detail = client.get(f"/workspace/investigation/{case_id}")
    report = client.get(f"/workspace/investigation/{case_id}/report")
    assert detail.status_code == 200
    assert report.status_code == 200
    assert b"Evidence" in detail.data
    assert b"IOC intelligence" in detail.data
    assert b"Evidence summary" in report.data
    assert b"synthetic_demo" in report.data


def test_start_failure_returns_safe_unavailable_response(application):
    client = application.test_client()
    register_and_login_analyst(client, "start-failure", "start-failure@example.test")
    client.get("/workspace/")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(tenant_id)
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    coordinator = application.container.require("investigation_coordinator")
    with patch.object(coordinator, "investigate", side_effect=RuntimeError("START_FAILURE_SENTINEL")):
        response = client.post(f"/workspace/investigation/{case_id}/start", headers={"X-CSRF-Token": token})
    assert response.status_code == 503
    assert b"START_FAILURE_SENTINEL" not in response.data
    assert b"Traceback" not in response.data


def test_report_projection_failure_returns_safe_unavailable_response(application):
    client = application.test_client()
    register_and_login_analyst(client, "report-failure", "report-failure@example.test")
    client.get("/workspace/")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(tenant_id)
    with patch("dashboard.browser_routes.AIInvestigatorReportService.build", side_effect=RuntimeError("REPORT_FAILURE_SENTINEL")):
        response = client.get(f"/workspace/investigation/{case_id}/report")
    assert response.status_code == 503
    assert b"REPORT_FAILURE_SENTINEL" not in response.data
    assert b"Traceback" not in response.data


def test_feedback_persistence_failure_returns_safe_unavailable_response(application):
    client = application.test_client()
    register_and_login_analyst(client, "feedback-failure", "feedback-failure@example.test")
    client.get("/workspace/")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(tenant_id)
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    coordinator = application.container.require("investigation_coordinator")
    with patch.object(coordinator, "submit_feedback", side_effect=RuntimeError("FEEDBACK_FAILURE_SENTINEL")):
        response = client.post(
            f"/workspace/investigation/{case_id}/feedback",
            json={"decision": "accepted", "helpful_rating": 5},
            headers={"X-CSRF-Token": token},
        )
    assert response.status_code == 503
    assert b"FEEDBACK_FAILURE_SENTINEL" not in response.data
    assert b"Traceback" not in response.data
    assert coordinator.get_feedback(case_id, tenant_id) == []


def test_disabled_demo_mode_preserves_honest_empty_states(application):
    application.config["DEMO_DATA_ENABLED"] = False
    client = application.test_client()
    register_and_login_analyst(client, "empty-user", "empty@example.test")
    assert b"No active investigations" in client.get("/workspace").data
    assert b"No active investigations" in client.get("/workspace/").data


def test_demo_case_is_not_readable_across_tenants(application):
    first = application.test_client()
    register_and_login_analyst(first, "first-user", "first@example.test")
    first.get("/workspace/")
    with first.session_transaction() as state:
        case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(state["organization_id"])

    second = application.test_client()
    register_and_login_analyst(second, "second-user", "second@example.test")
    assert second.get(f"/workspace/investigation/{case_id}").status_code == 404
    assert second.get(f"/workspace/investigation/{case_id}/report").status_code == 404


def test_analyst_feedback_is_authenticated_tenant_scoped_and_persistent(application):
    client = application.test_client()
    register_and_login_analyst(client, "feedback-user", "feedback@example.test")
    client.get("/workspace/")
    with client.session_transaction() as state:
        tenant_id = state["organization_id"]
    case_id = application.container.require("analyst_demo_scenario").case_id_for_tenant(tenant_id)
    csrf_token = client.get("/api/auth/csrf").get_json()["csrf_token"]

    response = client.post(
        f"/workspace/investigation/{case_id}/feedback",
        headers={"X-CSRF-Token": csrf_token},
        data={
            "action": "confirm",
            "helpful_rating": "5",
            "confidence_rating": "4",
            "estimated_time_saved": "30",
            "analyst_comments": "Investigation reduced from 45 minutes to 15 minutes.",
        },
    )
    assert response.status_code == 302
    feedback = application.container.require("investigation_coordinator").get_feedback(case_id, tenant_id)
    assert feedback[0]["tenant_id"] == tenant_id
    assert feedback[0]["analyst_id"]
    assert feedback[0]["helpful_rating"] == 5
    assert feedback[0]["confidence_rating"] == 4
    assert feedback[0]["estimated_time_saved"] == 30
    assert feedback[0]["created_at"]

    other = application.test_client()
    register_and_login_analyst(other, "other-feedback-user", "other-feedback@example.test")
    other_csrf = other.get("/api/auth/csrf").get_json()["csrf_token"]
    assert other.post(
        f"/workspace/investigation/{case_id}/feedback",
        headers={"X-CSRF-Token": other_csrf},
        data={
            "action": "confirm",
            "helpful_rating": "5",
            "confidence_rating": "5",
            "estimated_time_saved": "1",
            "analyst_comments": "cross tenant attempt",
        },
    ).status_code == 404
