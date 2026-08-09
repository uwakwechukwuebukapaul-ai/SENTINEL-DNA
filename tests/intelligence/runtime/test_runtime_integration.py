"""
Sentinel DNA Runtime Integration Tests
"""

from services.intelligence.runtime import (
    InvestigationRuntime,
    RuntimeContext,
)


class FakeReasoner:

    def reason(self, context):

        return {
            "risk": "high",
            "summary": "High risk investigation",
        }


class FakeRecommendationEngine:

    def generate(self, context):

        return {
            "recommendations": [
                "Contain threat",
            ]
        }


class FakeOrchestrator:

    def investigate(
        self,
        case_id,
        artifacts,
    ):

        return {

            "execution": {
                "action": "contain",
            },

            "report": {
                "status": "completed",
            },

        }


def create_runtime():

    return InvestigationRuntime(
        reasoner=FakeReasoner(),
        recommendation_engine=FakeRecommendationEngine(),
        orchestrator=FakeOrchestrator(),
    )


def test_runtime_context_creation():

    context = RuntimeContext(
        case_id="CASE-001",
        evidence=[
            {
                "type": "ioc",
                "value": "malicious-domain.xyz",
            }
        ],
    )

    assert context.case_id == "CASE-001"

    assert len(context.evidence) == 1


def test_runtime_execution():

    runtime = create_runtime()

    result = runtime.execute(
        case_id="CASE-001",
        evidence=[],
    )

    assert result["status"] == "completed"


def test_runtime_investigation_result():

    runtime = create_runtime()

    result = runtime.execute(
        case_id="CASE-002",
        evidence=[],
    )

    assert (
        result["investigation"]["analysis"]["risk"]
        == "high"
    )


def test_runtime_execution_result():

    runtime = create_runtime()

    result = runtime.execute(
        case_id="CASE-003",
        evidence=[],
    )

    assert (
        result["execution"]["action"]
        == "contain"
    )


def test_runtime_report_result():

    runtime = create_runtime()

    result = runtime.execute(
        case_id="CASE-004",
        evidence=[],
    )

    assert (
        result["report"]["status"]
        == "completed"
    )