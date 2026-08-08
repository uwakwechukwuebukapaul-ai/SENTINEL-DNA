from services.intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)



def test_investigation_orchestrator():

    orchestrator = (
        InvestigationOrchestrator()
    )


    result = orchestrator.investigate(

        case_id="CASE-001",

        alert={
            "indicator":
            "evil-domain.xyz"
        },

    )


    assert result.case_id == "CASE-001"


    assert "plan" in result.results