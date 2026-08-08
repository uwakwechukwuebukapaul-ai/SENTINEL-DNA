from services.intelligence.orchestration.investigation_context import (
    InvestigationContext,
)



def test_investigation_context():

    context = InvestigationContext(

        case_id="CASE-001",

        alert={
            "type": "phishing"
        },

    )


    context.add_result(
        "risk",
        "HIGH",
    )


    assert (
        context.results["risk"]
        ==
        "HIGH"
    )