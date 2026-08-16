from services.intelligence.investigation_decision.decision_service import InvestigationDecisionService


def test_decision_service_is_deterministic_tenant_scoped_and_advisory():
    first = InvestigationDecisionService().derive("tenant-a")
    repeat = InvestigationDecisionService().derive("tenant-a")
    other = InvestigationDecisionService().derive("tenant-b")
    assert first["analysis"]["analysis_id"] == repeat["analysis"]["analysis_id"]
    assert first["analysis"]["analysis_id"] != other["analysis"]["analysis_id"]
    assert first["advisory_only"] is True
    assert first["analysis"]["decision_posture"] == "insufficient_evidence"
