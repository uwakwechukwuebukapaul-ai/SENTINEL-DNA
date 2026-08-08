"""
Sentinel DNA Investigation Service Tests

Validates investigation service workflow.
"""

from __future__ import annotations


from services.intelligence.investigation.investigation_service import (
    InvestigationService,
)

from services.intelligence.investigation.execution_orchestrator import (
    InvestigationExecutionOrchestrator,
)

from services.intelligence.investigation.investigation_pipeline import (
    InvestigationPipeline,
)



class FakeInvestigationEngine:
    """
    Fake engine used for testing.
    """

    def analyze(
        self,
        alert,
    ):

        return {
            "analysis": "completed",
            "severity": alert.get(
                "severity",
                "unknown",
            ),
        }



def create_service():

    pipeline = InvestigationPipeline()


    pipeline.register_engine(
        "analysis_engine",
        FakeInvestigationEngine(),
    )


    orchestrator = (
        InvestigationExecutionOrchestrator(
            pipeline=pipeline
        )
    )


    return InvestigationService(
        orchestrator=orchestrator
    )



def test_service_initialization():

    service = create_service()

    assert service is not None



def test_investigation_execution():

    service = create_service()


    result = service.investigate(
        case_id="CASE-500",
        alert={
            "source": "email",
            "severity": "high",
        },
    )


    assert (
        result.case_id
        ==
        "CASE-500"
    )


    assert (
        "analysis_engine"
        in result.findings
    )



def test_get_investigation_history():

    service = create_service()


    service.investigate(
        case_id="CASE-600",
        alert={
            "source": "endpoint",
        },
    )


    history = (
        service.get_investigation_history()
    )


    assert len(history) == 1


    assert (
        history[0]["case_id"]
        ==
        "CASE-600"
    )



def test_clear_investigation_history():

    service = create_service()


    service.investigate(
        case_id="CASE-700",
        alert={
            "source": "network",
        },
    )


    service.clear_history()


    assert (
        service.get_investigation_history()
        ==
        []
    )