from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator


def result():
    return InvestigationResult(
        status="completed",
        case_id="CASE-1",
        artifacts=[{"evidence_id": "E-1", "description": "phishing indicator"}],
        findings=[{
            "finding_id": "RF-1",
            "evidence_refs": ["E-1"],
            "intelligence_provenance": {
                "providers": ["provider-a", "provider-z"],
                "status": ["stale"],
                "disposition": "supporting",
            },
        }],
        recommendations=["Escalate for analyst review"],
        recommendation_sources=[],
        risk={"score": 80, "severity": "high"},
        confidence=0.88,
        mitre=["T1566"],
        timeline=[{"event": "email received"}],
        reasoning_report={
            "summary": "Evidence supports a potential credential harvesting attempt.",
            "findings": [],
        },
        threat_intelligence_report={"status": "available"},
        tenant_context={"tenant_id": "tenant-a", "actor_id": "actor-a"},
        intelligence={"normalized": {"metadata": {"intelligence_status": {
            "statuses": ["stale"], "disposition": "supporting"
        }}}},
        decision_report={"metadata": {"governance": {
            "mode": "ADVISORY_ONLY",
            "analyst_authority_required": True,
            "autonomous_action": False,
        }}},
    )


def test_result_transforms_to_evidence_backed_analyst_report():
    report = InvestigationReportGenerator().generate_from_result(result())
    data = report.to_dict()
    assert data["case_id"] == "CASE-1"
    assert data["status"] == "completed"
    assert data["risk"]["score"] == 80
    assert data["findings"][0]["evidence_refs"] == ["E-1"]
    assert data["evidence"] == [{"evidence_id": "E-1", "description": "phishing indicator"}]
    assert data["threat_intelligence"] == {"status": "available"}
    assert data["intelligence_disposition"] == {"status": ["stale"], "disposition": "supporting"}
    assert data["mitre"] == ["T1566"]
    assert data["timeline"] == [{"event": "email received"}]
    assert data["recommendations"] == ["Escalate for analyst review"]
    assert data["governance"]["mode"] == "ADVISORY_ONLY"
    assert data["tenant_context"] == {"tenant_id": "tenant-a", "actor_id": "actor-a"}


def test_report_is_deterministic_and_does_not_fabricate_optional_data():
    first = InvestigationReportGenerator().generate_from_result(InvestigationResult(case_id="CASE-2"))
    second = InvestigationReportGenerator().generate_from_result(InvestigationResult(case_id="CASE-2"))
    first_data = first.to_dict()
    second_data = second.to_dict()
    assert first_data["case_id"] == second_data["case_id"] == "CASE-2"
    assert first_data["findings"] == second_data["findings"] == []
    assert first_data["evidence"] == second_data["evidence"] == []
    assert first_data["threat_intelligence"] == "unavailable"
    assert first_data["intelligence_disposition"] == {"status": [], "disposition": "unavailable"}
    assert first_data["tenant_context"] == "unavailable"
    assert first_data["recommendations"] == []


def test_report_preserves_empty_recommendation_sources():
    report = InvestigationReportGenerator().generate_from_result(result())
    assert report.to_dict()["metadata"]["recommendation_sources"] == []
