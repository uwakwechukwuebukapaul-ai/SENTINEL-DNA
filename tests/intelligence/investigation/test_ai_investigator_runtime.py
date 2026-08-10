"""
Sentinel DNA AI Investigator Runtime Tests.

Validates the complete investigation execution path.
"""

from services.intelligence.investigation.runtime import (
    AIInvestigatorRuntime,
)  # pyright: ignore[reportMissingImports]


def test_ai_investigator_runtime_initialization():

    runtime = AIInvestigatorRuntime()

    assert runtime is not None
    assert runtime.correlation is not None
    assert runtime.reasoning is not None
    assert runtime.fusion is not None
    assert runtime.reporting is not None


def test_ai_investigator_runtime_malicious_case():

    runtime = AIInvestigatorRuntime()

    result = runtime.investigate(
        "CASE-RUNTIME-001",
        {
            "sender": "attacker@evil.xyz",
            "url": "http://login-phish.xyz",
            "severity": "high",
        },
    )

    assert result["case_id"] == "CASE-RUNTIME-001"

    assert result["status"] == "completed"

    assert isinstance(
        result["report"],
        dict,
    )

    assert result["report"]

    assert (
        result["metadata"]["engine"]
        == "ai_investigator_runtime"
    )


def test_ai_investigator_runtime_low_risk_case():

    runtime = AIInvestigatorRuntime()

    result = runtime.investigate(
        "CASE-RUNTIME-002",
        {
            "source": "internal-system",
            "severity": "low",
        },
    )

    assert result["case_id"] == "CASE-RUNTIME-002"

    assert result["status"] == "completed"

    assert isinstance(
        result["report"],
        dict,
    )


def test_ai_investigator_runtime_pipeline_metadata():

    runtime = AIInvestigatorRuntime()

    result = runtime.investigate(
        "CASE-RUNTIME-003",
        {
            "source": "email",
            "severity": "high",
        },
    )

    stages = result["metadata"]["stages"]

    assert "correlation" in stages

    assert "reasoning" in stages

    assert "fusion" in stages

    assert "reporting" in stages