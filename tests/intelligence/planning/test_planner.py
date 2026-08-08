from services.intelligence.planning import (
    InvestigationPlanner,
)



def test_create_plan():

    planner = InvestigationPlanner()


    result = planner.create_plan(
        {
            "id": "INV-001",
            "severity": "medium",
        }
    )


    assert (
        result["status"]
        == "planned"
    )



def test_high_risk_plan():

    planner = InvestigationPlanner()


    result = planner.create_plan(
        {
            "severity": "critical",
        }
    )


    assert (
        "map MITRE techniques"
        in result["steps"]
    )



def test_plan_history():

    planner = InvestigationPlanner()


    planner.create_plan({})


    assert len(
        planner.get_history()
    ) == 1



def test_clear_history():

    planner = InvestigationPlanner()


    planner.create_plan({})

    planner.clear_history()


    assert planner.get_history() == []