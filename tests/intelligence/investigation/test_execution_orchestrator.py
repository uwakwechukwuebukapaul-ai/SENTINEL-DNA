"""
Sentinel DNA Investigation Execution Orchestrator Tests

Validates autonomous investigation execution workflow.
"""

from __future__ import annotations


from services.intelligence.investigation.execution_orchestrator import (
    InvestigationExecutionOrchestrator,
)

from services.intelligence.investigation.investigation_pipeline import (
    InvestigationPipeline,
)



class FakeThreatIntelEngine:
    """
    Fake threat intelligence engine.
    """

    def analyze(
        self,
        alert,
    ):

        return {
            "ioc": "malicious.example.com",
            "reputation": "malicious",
            "confidence": 95,
        }



class FakeRiskEngine:
    """
    Fake risk intelligence engine.
    """

    def analyze(
        self,
        alert,
    ):

        return {
            "risk_score": 90,
            "severity": "critical",
        }



def create_orchestrator():

    pipeline = InvestigationPipeline()

    pipeline.register_engine(
        "threat_intelligence",
        FakeThreatIntelEngine(),
    )

    pipeline.register_engine(
        "risk_engine",
        FakeRiskEngine(),
    )

    return InvestigationExecutionOrchestrator(
        pipeline=pipeline
    )



def test_execute_investigation():

    orchestrator = create_orchestrator()


    result = orchestrator.execute_investigation(
        case_id="CASE-100",
        alert={
            "source": "email",
            "severity": "high",
        },
    )


    assert result.case_id == "CASE-100"

    assert result.status == "completed"

    assert (
        "threat_intelligence"
        in result.findings
    )

    assert (
        "risk_engine"
        in result.findings
    )



def test_execution_history():

    orchestrator = create_orchestrator()


    orchestrator.execute_investigation(
        case_id="CASE-200",
        alert={
            "source": "endpoint",
            "severity": "critical",
        },
    )


    history = (
        orchestrator.get_history()
    )


    assert len(history) == 1

    assert (
        history[0]["case_id"]
        ==
        "CASE-200"
    )



def test_clear_execution_history():

    orchestrator = create_orchestrator()


    orchestrator.execute_investigation(
        case_id="CASE-300",
        alert={
            "source": "network",
        },
    )


    orchestrator.clear_history()


    assert (
        orchestrator.get_history()
        == []
    )