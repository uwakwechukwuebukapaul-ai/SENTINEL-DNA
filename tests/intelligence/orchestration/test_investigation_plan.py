from services.intelligence.orchestration.investigation_plan import (
    InvestigationPlan,
)



def test_investigation_plan():

    plan = InvestigationPlan(
        case_id="CASE-001"
    )


    plan.add_stage(
        "risk_analysis"
    )


    assert (
        "risk_analysis"
        in plan.stages
    )