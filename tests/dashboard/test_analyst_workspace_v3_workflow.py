from services.intelligence.models.investigation_intelligence import InvestigationIntelligence


def _seed(client, case_id="CASE-V3", tenant_id="tenant-a"):
    coordinator = client.application.container.require("investigation_coordinator")
    coordinator.intelligence_repository.save(
        case_id,
        InvestigationIntelligence(
            risk_score=92,
            confidence=0.88,
            findings=["Credential access observed"],
            iocs=[{"value": "evil.example"}],
            mitre_techniques=["T1078"],
            metadata={"tenant_id": tenant_id},
        ),
    )
    coordinator.report_repository.save({
        "case_id": case_id,
        "status": "investigating",
        "risk_score": 92,
        "confidence": 0.88,
        "findings": ["Credential access observed"],
        "evidence": [{"evidence_id": "E-1", "source": "evidence-engine"}],
        "relationships": [{"source": "E-1", "target": "evil.example", "relation": "indicates"}],
        "mitre": ["T1078"],
        "reasoning_report": "The evidence supports a credential access hypothesis.",
        "recommendations": ["Validate the affected account and preserve telemetry."],
        "tenant_context": {"tenant_id": tenant_id},
    })


def test_investigation_detail_renders_canonical_workflow_sections(canonical_authenticated_client):
    _seed(canonical_authenticated_client)

    response = canonical_authenticated_client.get("/workspace/investigation/CASE-V3")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    for label in ("Investigation detail", "RISK SCORE", "CONFIDENCE", "Findings", "Evidence", "IOC relationships", "MITRE mappings", "AI reasoning report", "Recommendations"):
        assert label in body
    assert "Credential access observed" in body
    assert "evil.example" in body
    assert "T1078" in body
    assert "preserve telemetry" in body
    assert "Start Investigation" in body


def test_start_investigation_requires_csrf_and_uses_coordinator(canonical_authenticated_client, monkeypatch):
    _seed(canonical_authenticated_client)
    coordinator = canonical_authenticated_client.application.container.require("investigation_coordinator")
    calls = []

    def fake_investigate(**kwargs):
        calls.append(kwargs)
        return {"success": True, "case_id": kwargs["case_id"]}

    monkeypatch.setattr(coordinator, "investigate", fake_investigate)
    assert canonical_authenticated_client.post("/workspace/investigation/CASE-V3/start").status_code == 403
    with canonical_authenticated_client.session_transaction() as state:
        state["csrf_token"] = "csrf-v3"
    response = canonical_authenticated_client.post(
        "/workspace/investigation/CASE-V3/start",
        headers={"X-CSRF-Token": "csrf-v3"},
    )
    assert response.status_code == 302
    assert calls and calls[0]["case_id"] == "CASE-V3"
    assert calls[0]["tenant_id"] == "tenant-a"


def test_start_investigation_preserves_viewer_rbac(canonical_authenticated_client):
    _seed(canonical_authenticated_client)
    with canonical_authenticated_client.application.container.require("canonical_authority").db.session() as connection:
        connection.execute("UPDATE canonical_memberships SET role='viewer' WHERE tenant_id=? AND actor_id=?", ("tenant-a", "actor-a"))
    with canonical_authenticated_client.session_transaction() as state:
        state["csrf_token"] = "csrf-v3"
    response = canonical_authenticated_client.post(
        "/workspace/investigation/CASE-V3/start",
        headers={"X-CSRF-Token": "csrf-v3"},
    )
    assert response.status_code == 403
