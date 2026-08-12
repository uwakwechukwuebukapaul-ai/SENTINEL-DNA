import json

import pytest

from sentinel_dna.investigation.reporting import InvestigationReporter
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
    assert (
        result.results["decision_intelligence"]["recommended_decision"]
        == "escalate"
    )
    assert result.results["report"]["recommended_actions"]
    assert set(result.to_dict()) == {
        "plan_name",
        "results",
        "errors",
    }
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

    assert (
        result.results["intelligence"]["iocs"][
            "https://example-login.com"
        ]["reputation"]
        == "suspicious"
    )

    assert (
        result.results["correlations"][0]["relationship"]
        == "observed_in_evidence"
    )

    assert (
        result.results["timeline"][0]["evidence_id"]
        == result.results["evidence"][0]["evidence_id"]
    )

    assert result.results["mitre_attack"][0]["technique_id"] == "T1566"
    assert result.results["fusion"]["verdict"] in {
        "suspicious",
        "malicious",
    }
    assert "EvidenceFusionEngine" == result.results["fusion"]["metadata"]["engine"]
    assert (
        result.results["threat_classification"]["classification"]
        == "phishing"
    )

    assert (
        result.results["reasoning"]["findings"][0]["evidence_id"]
        == result.results["evidence"][0]["evidence_id"]
    )

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

    assert (
        "No IOCs were discovered in the submitted alert evidence."
        in result.results["uncertainties"]
    )

    assert result.results["confidence"]["uncertainties"]
    assert result.errors == []


def test_investigate_rejects_malformed_input(tmp_path):
    coordinator = InvestigationCoordinator(tmp_path)

    with pytest.raises(ValueError, match="case_id"):
        coordinator.investigate("", {"subject": "Alert"})

    with pytest.raises(ValueError, match="alert"):
        coordinator.investigate("case-invalid-001", {})


def test_runtime_task_executor_records_structured_non_required_errors():
    context = InvestigationContext(
        case_id="case-runtime-001",
        alert={},
    )

    executor = RuntimeTaskExecutor()

    def fail(_context):
        raise ValueError("source unavailable")

    executor.execute(
        context,
        [
            RuntimeTask("optional_intel", fail),
            RuntimeTask(
                "required_followup",
                lambda investigation_context: (
                    investigation_context.uncertainties.append(
                        "continued"
                    )
                ),
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


def test_orchestrator_creates_execution_plan_only_once(tmp_path):
    class CountingPlanner:
        plan_name = "ai-investigator-v1"

        def __init__(self):
            self.calls = 0

        def create_plan(self, context, orchestrator):
            self.calls += 1
            return [
                RuntimeTask(
                    "load_context",
                    orchestrator.load_context,
                    required=True,
                ),
                RuntimeTask(
                    "collect_evidence",
                    orchestrator.collect_evidence,
                    required=True,
                ),
            ]

    planner = CountingPlanner()
    orchestrator = InvestigationOrchestrator(
        tmp_path,
        planner=planner,
    )

    context = InvestigationContext(
        case_id="case-plan-once-001",
        alert={
            "subject": "Suspicious login",
            "body": "Verify at https://example-login.com.",
        },
    )

    result = orchestrator.run(context)

    assert planner.calls == 1
    assert result.results["plan"]["tasks"] == [
        "load_context",
        "collect_evidence",
    ]


def test_investigation_engine_exposes_public_recommendation_api():
    engine = InvestigationReporter()

    high_actions = engine.recommend_actions("high")
    medium_actions = engine.recommend_actions("medium")
    low_actions = engine.recommend_actions("low")

    assert high_actions
    assert medium_actions
    assert low_actions
    assert "Escalate to senior analyst." in high_actions


def test_orchestrator_uses_public_recommendation_api(tmp_path):
    orchestrator = InvestigationOrchestrator(tmp_path)

    calls = []

    def recommend_actions(level):
        calls.append(level)
        return ["test recommendation"]

    orchestrator.investigation_engine.recommend_actions = recommend_actions

    context = InvestigationContext(
        case_id="case-public-api-001",
        alert={
            "subject": "Routine update",
            "body": "No indicators included.",
        },
    )

    result = orchestrator.run(context)

    assert calls == ["low"]
    assert result.results["recommendations"] == [
        "test recommendation"
    ]


def test_execution_plan_matches_executed_tasks(tmp_path):
    orchestrator = InvestigationOrchestrator(tmp_path)

    context = InvestigationContext(
        case_id="case-plan-trace-001",
        alert={
            "subject": "Suspicious login",
            "body": "Verify at https://example-login.com.",
        },
    )

    result = orchestrator.run(context)

    planned_tasks = result.results["plan"]["tasks"]
    executed_tasks = [
        item["task"]
        for item in result.results["tasks"]
    ]

    assert planned_tasks == executed_tasks
    assert planned_tasks.index("fuse_evidence") < planned_tasks.index(
        "calculate_risk"
    )
    assert planned_tasks.index("calculate_confidence") < planned_tasks.index(
        "perform_reasoning"
    )


def test_phishing_investigation_creates_lineage_replay_and_reasoning(tmp_path):
    result = InvestigationCoordinator(tmp_path).investigate(
        "case-phishing-final-001",
        {
            "sender": "security@example-login.com",
            "subject": "Password verification required",
            "body": "Confirm MFA and password at https://example-login.com/security.",
            "severity": "high",
        },
    )

    output = result.results

    assert result.errors == []
    assert output["investigation"]["status"] == "completed"
    assert output["intelligence"]["threat"]["suspicious_iocs"]
    assert output["mitre_attack"][0]["technique_id"] == "T1566"
    assert output["fusion"]["evidence_count"] >= 3
    assert output["risk"]["score"] >= 50
    assert output["reasoning"]["trace"]["supporting_evidence"]
    assert output["decision_intelligence"]["recommended_decision"] == "escalate"
    assert output["provenance"]["records"]
    assert output["replay"]["events"]
    assert output["audit_trail"]
