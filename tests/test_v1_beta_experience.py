from sentinel_dna.investigation import InvestigationCoordinator
from sentinel_dna.investigation.analyst_actions import AnalystActionService
from sentinel_dna.workspace.web_app import create_app


def test_report_contains_response_detection_and_audit_sections(tmp_path):
    result = InvestigationCoordinator(tmp_path).investigate("beta-report-001", {
        "sender": "security@example-login.com", "subject": "Urgent MFA verification",
        "body": "Verify password at https://example-login.com/security", "severity": "high",
    }).results

    report = result["report"]
    assert report["investigation_overview"]["case_id"] == "beta-report-001"
    assert report["attack_narrative"]
    assert report["response_recommendations"]
    assert report["detection_recommendations"][0]["sigma_rule"]["title"]
    assert report["format_version"] == "1.0"


def test_analyst_actions_are_validated_and_audited(tmp_path):
    InvestigationCoordinator(tmp_path).investigate("beta-action-001", {"subject": "Alert", "body": "https://example-login.com"})
    action = AnalystActionService(tmp_path).record("beta-action-001", "escalate", "A. Analyst", "Confirmed phishing")

    assert action["status"] == "escalated"
    assert action["audit_event"]["note"] == "Confirmed phishing"


def test_dashboard_and_detail_views_render(tmp_path):
    InvestigationCoordinator(tmp_path).investigate("beta-dashboard-001", {"subject": "Alert", "body": "https://example-login.com"})
    client = create_app(str(tmp_path)).test_client()

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert b"beta-dashboard-001" in dashboard.data
    assert client.get("/investigations/beta-dashboard-001").status_code == 200
    assert client.post("/investigations/beta-dashboard-001/actions", data={
        "action": "add_note", "analyst": "A. Analyst", "note": "Reviewed",
    }).status_code == 302
