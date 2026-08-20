from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator
from services.intelligence.investigation.decision import DecisionIntelligenceEngine


def test_report_preserves_legacy_fields_and_exposes_decision_intelligence():
    result = InvestigationResult(case_id="case-1", risk={"score": 55}, confidence=70, artifacts=[{"id": "a-1", "source": "edr"}])
    result.decision_intelligence = DecisionIntelligenceEngine().evaluate(result, tenant_id="tenant-a")
    report = InvestigationReportGenerator().generate_from_result(result)
    payload = report.to_dict()
    assert payload["decision_intelligence"]["investigation_id"] == "case-1"
    assert "reasoning_report" in payload
    assert "recommendations" in payload
