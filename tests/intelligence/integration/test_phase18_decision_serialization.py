"""Regression coverage for the Phase 18.1 decision serialization boundary."""

import json

from services.intelligence.investigation.decision import DecisionIntelligenceEngine, DecisionResult
from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator


def test_result_and_report_are_json_safe_without_decision_back_references():
    result = InvestigationResult(
        case_id="phase18-case",
        risk={"score": 90},
        confidence=80,
        artifacts=[{"id": "evidence-1", "source": "edr"}],
        intelligence={"normalized": {"status": "complete"}},
    )
    decision = DecisionIntelligenceEngine().evaluate(result, tenant_id="tenant-1")
    result.decision_intelligence = decision

    report = InvestigationReportGenerator().generate_from_result(result)
    result.intelligence["report"] = report.to_dict()

    result_payload = result.to_dict()
    report_payload = report.to_dict()

    assert json.loads(json.dumps(result_payload))["decision_intelligence"]["verdict"] == decision.verdict
    assert json.loads(json.dumps(report_payload))["decision_intelligence"]["provenance"]["engine"] == "decision_intelligence"
    assert report.intelligence is not result.intelligence


def test_decision_result_snapshots_objects_instead_of_retaining_them():
    result = InvestigationResult(case_id="phase18-case")
    decision = DecisionResult(provenance={"source_result": result})

    payload = decision.to_dict()

    assert isinstance(decision.provenance["source_result"], dict)
    assert isinstance(payload["provenance"]["source_result"], dict)
    assert payload["provenance"]["source_result"] is not result
    json.dumps(payload)
