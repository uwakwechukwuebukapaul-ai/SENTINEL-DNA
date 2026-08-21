from services.intelligence.investigation.experience_projection import project_analyst_experience


def test_projection_is_deterministic_and_redacts_sensitive_fields():
    report = {
        "case_id": "CASE-1", "title": "Alert", "severity": "HIGH", "status": "completed",
        "confidence": 0.9, "summary": "Suspicious execution",
        "evidence": [{"evidence_id": "E-1", "tenant_id": "T-1", "description": "Script"}],
        "findings": [{"finding_id": "F-1", "tenant_id": "T-1", "title": "Execution", "description": "Observed", "evidence_refs": ["E-1"], "confidence": .9}],
        "reasoning": {"summary": "Evidence supports execution", "confidence": .9},
        "decision_report": {"verdict": "true_positive", "confidence": .9, "evidence_summary": {"count": 1}},
        "api_key": "secret", "prompt": "hidden",
    }
    first = project_analyst_experience(report, tenant_id="T-1", case_id="CASE-1")
    second = project_analyst_experience(report, tenant_id="T-1", case_id="CASE-1")
    assert first == second
    assert first["verdict"]["label"] == "TRUE POSITIVE"
    assert first["reasoning"][0]["evidence"] == ["E-1"]
    assert "api_key" not in str(first)
    assert "hidden" not in str(first)


def test_projection_excludes_cross_tenant_nested_records_and_marks_phases():
    report = {
        "case_id": "CASE-1", "tenant_context": {"tenant_id": "T-1"},
        "evidence": [
            {"evidence_id": "owned", "tenant_id": "T-1"},
            {"evidence_id": "foreign", "tenant_id": "T-2"},
        ],
        "attack_story": {"phases": ["initial_access", "execution"]},
    }
    view = project_analyst_experience(report, tenant_id="T-1", case_id="CASE-1")
    assert [item["evidence_id"] for item in view["evidence"]] == ["owned"]
    assert view["attack_reconstruction"]["phases"][0]["supported"] is True
    assert view["attack_reconstruction"]["phases"][-1]["supported"] is False
