from services.intelligence.models.investigation_intelligence import InvestigationIntelligence
from services.intelligence.reporting.ai_investigator_report import AIInvestigatorReportService


def _seed(client):
    coordinator = client.application.container.require("investigation_coordinator")
    coordinator.intelligence_repository.save(
        "CASE-REPORT",
        InvestigationIntelligence(
            risk_score=79,
            risk_severity="high",
            confidence=0.84,
            findings=["Suspicious authentication"],
            iocs=[{"value": "evil.example", "type": "domain"}],
            mitre_techniques=["T1078"],
            timeline=[{"event_id": "T-1", "description": "Alert observed", "timestamp": "2026-08-21T10:00:00Z"}],
            metadata={"tenant_id": "tenant-a"},
        ),
    )
    coordinator.report_repository.save({
        "case_id": "CASE-REPORT",
        "title": "Authentication incident",
        "status": "completed",
        "severity": "high",
        "risk": {"score": 79, "severity": "high"},
        "confidence": 0.84,
        "summary": "An authentication incident requires review.",
        "evidence": [{"evidence_id": "E-1", "source": "evidence-engine"}],
        "provider_observations": [{"provider": "offline", "value": "evil.example", "confidence": 0.91}],
        "relationships": [{"source": "E-1", "target": "evil.example", "relation": "indicates"}],
        "reasoning_report": {"summary": "Evidence supports suspicious activity.", "explanation": "The observed login matches the indicator."},
        "mitre": [{"technique_id": "T1078", "name": "Valid Accounts"}],
        "recommendations": ["Validate the account and preserve logs."],
        "analyst_actions": ["Review supporting evidence."],
        "timeline": [{"event_id": "T-1", "description": "Alert observed", "timestamp": "2026-08-21T10:00:00Z"}],
        "tenant_context": {"tenant_id": "tenant-a"},
    })


def test_report_projection_composes_existing_snapshot_and_report_contracts(canonical_authenticated_client):
    _seed(canonical_authenticated_client)
    coordinator = canonical_authenticated_client.application.container.require("investigation_coordinator")
    context = type("Context", (), {"tenant_id": "tenant-a"})()

    report = AIInvestigatorReportService().build(coordinator, "CASE-REPORT", "tenant-a", context)

    assert report is not None
    payload = report.to_dict()
    assert payload["executive_summary"] == "An authentication incident requires review."
    assert payload["severity"] == "high"
    assert payload["risk"]["score"] == 79
    assert payload["evidence_summary"]["count"] == 1
    assert payload["ioc_intelligence"][0]["provider"] == "offline"
    assert payload["mitre_mappings"][0]["technique_id"] == "T1078"
    assert payload["relationships"][0]["relation"] == "indicates"
    assert payload["analyst_actions"] == ["Review supporting evidence."]


def test_report_route_is_authenticated_and_tenant_scoped(canonical_authenticated_client):
    _seed(canonical_authenticated_client)
    client = canonical_authenticated_client
    assert client.get("/workspace/investigation/CASE-REPORT/report").status_code == 200
    body = client.get("/workspace/investigation/CASE-REPORT/report").get_data(as_text=True)
    for label in ("Incident investigation report", "Executive summary", "Timeline", "Evidence summary", "IOC intelligence", "MITRE mappings", "AI reasoning explanation", "Recommendations", "Analyst actions"):
        assert label in body
    assert "Valid Accounts" in body
    assert "preserve logs" in body


def test_report_route_does_not_leak_another_tenant(canonical_authenticated_client):
    _seed(canonical_authenticated_client)
    coordinator = canonical_authenticated_client.application.container.require("investigation_coordinator")
    coordinator.report_repository.save({"case_id": "CASE-OTHER", "summary": "Other tenant", "tenant_context": {"tenant_id": "tenant-b"}})
    assert canonical_authenticated_client.get("/workspace/investigation/CASE-OTHER/report").status_code == 404
