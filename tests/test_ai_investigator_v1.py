import json

import pytest

from sentinel_dna.investigation import (
    InvestigationContext,
    InvestigationCoordinator,
    InvestigationOrchestrator,
    RuntimeTaskExecutor,
)
from sentinel_dna.investigation.runtime import RuntimeTask


def test_investigate_preserves_public_result_contract(tmp_path):
    coordinator = InvestigationCoordinator(tmp_path)

    result = coordinator.investigate(
        "case-contract-001",
        {
            "sender": "security-alert@example-login.com",
            "subject": "Urgent MFA password verification required",
            "body": "Verify your password at https://example-login.com/security.",
            "severity": "high",
        },
    )

    assert result.plan_name == "ai-investigator-v1"
    assert result.errors == []
    assert result.results["plan"]["name"] == "ai-investigator-v1"
    assert result.results["tasks"]
    assert result.results["case_id"] == "case-contract-001"
    assert "https://example-login.com/security" in result.results["iocs"]
    assert result.results["risk"]["score"] > 0
    assert result.results["confidence"]["score"] > 0
    assert result.results["decision_intelligence"]["recommended_decision"] == "escalate"
    assert result.results["report"]["recommended_actions"]
    assert set(result.to_dict()) == {"plan_name", "results", "errors"}
    json.dumps(result.to_dict())


def test_orchestrator_runs_evidence_first_pipeline(tmp_path):
    orchestrator = InvestigationOrchestrator(tmp_path)
    context = InvestigationContext(
        case_id="case-pipeline-001",
        alert={
            "sender": "unknown@example.com",
            "subject": "Suspicious login verification",
            "body": "User clicked https://example-login.com.",
        },
    )

    result = orchestrator.run(context)

    assert result.results["evidence"]
    assert result.results["intelligence"]["iocs"]["https://example-login.com"]["reputation"] == "suspicious"
    assert result.results["correlations"][0]["relationship"] == "observed_in_evidence"
    assert result.results["timeline"][0]["evidence_id"] == result.results["evidence"][0]["evidence_id"]
    assert result.results["mitre_attack"][0]["technique_id"] == "T1566"
    assert result.results["threat_classification"]["classification"] == "phishing"
    assert result.results["reasoning"]["findings"][0]["evidence_id"] == result.results["evidence"][0]["evidence_id"]
    assert result.results["decision_intelligence"]["rationale"]
    assert result.results["audit_trail"][-1]["stage"] == "generate_report"


def test_missing_evidence_is_represented_as_uncertainty(tmp_path):
    coordinator = InvestigationCoordinator(tmp_path)

    result = coordinator.investigate(
        "case-uncertain-001",
        {
            "subject": "Routine update",
            "body": "No links or indicators included.",
        },
    )

    assert "No IOCs were discovered in the submitted alert evidence." in result.results["uncertainties"]
    assert result.results["confidence"]["uncertainties"]
    assert result.errors == []


def test_investigate_rejects_malformed_input(tmp_path):
    coordinator = InvestigationCoordinator(tmp_path)

    with pytest.raises(ValueError, match="case_id"):
        coordinator.investigate("", {"subject": "Alert"})

    with pytest.raises(ValueError, match="alert"):
        coordinator.investigate("case-invalid-001", {})


def test_runtime_task_executor_records_structured_non_required_errors():
    context = InvestigationContext(case_id="case-runtime-001", alert={})
    executor = RuntimeTaskExecutor()

    def fail(_context):
        raise ValueError("source unavailable")

    executor.execute(
        context,
        [
            RuntimeTask("optional_intel", fail),
            RuntimeTask(
                "required_followup",
                lambda investigation_context: investigation_context.uncertainties.append("continued"),
                required=True,
            ),
        ],
    )

    assert context.errors == [
        {
            "stage": "optional_intel",
            "type": "ValueError",
            "message": "source unavailable",
            "required": False,
        }
    ]
    assert context.task_results[0]["status"] == "failed"
    assert context.audit_trail[0]["status"] == "failed"
    assert context.uncertainties == ["continued"]
