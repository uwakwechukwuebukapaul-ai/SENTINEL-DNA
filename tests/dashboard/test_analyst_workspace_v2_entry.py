from services.intelligence.models.investigation_intelligence import InvestigationIntelligence


def _seed(client, case_id, tenant_id, status="investigating"):
    coordinator = client.application.container.require("investigation_coordinator")
    coordinator.intelligence_repository.save(
        case_id,
        InvestigationIntelligence(
            risk_score=87,
            risk_severity="high",
            confidence=0.91,
            iocs=[{"value": "evil.example"}],
            timeline=[{"type": "alert", "description": "Suspicious login", "created_at": "2026-08-21T10:00:00Z"}],
            metadata={"tenant_id": tenant_id},
        ),
    )
    coordinator.report_repository.save({
        "case_id": case_id,
        "title": "Credential attack",
        "status": status,
        "confidence": 0.91,
        "evidence": [{"id": "e-1"}, {"id": "e-2"}],
        "tenant_context": {"tenant_id": tenant_id},
    })


def test_workspace_entry_requires_authentication(isolated_shared_database):
    from app import create_app

    application = create_app()
    application.config["TESTING"] = True
    assert application.test_client().get("/workspace/").status_code == 401


def test_workspace_entry_projects_identity_metrics_and_alerts(canonical_authenticated_client):
    _seed(canonical_authenticated_client, "CASE-A", "tenant-a")

    response = canonical_authenticated_client.get("/workspace/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "canonical@example.com" in body
    assert "Acme" in body
    assert "CASE-A" in body
    assert "91%" in body
    assert "87" in body
    assert "Suspicious login" in body
    assert ">2<" in body
    assert ">1<" in body


def test_workspace_entry_is_tenant_isolated(canonical_authenticated_client):
    _seed(canonical_authenticated_client, "CASE-A", "tenant-a")
    _seed(canonical_authenticated_client, "CASE-B", "tenant-b")

    body = canonical_authenticated_client.get("/workspace/").get_data(as_text=True)
    assert "CASE-A" in body
    assert "CASE-B" not in body
