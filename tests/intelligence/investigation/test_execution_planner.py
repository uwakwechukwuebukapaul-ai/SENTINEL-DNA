"""
Sentinel DNA Execution Planner Tests
"""

from __future__ import annotations


from services.intelligence.investigation.execution_planner import (
    InvestigationExecutionPlanner,
)



def test_create_plan():

    planner = InvestigationExecutionPlanner()


    plan = planner.create_plan(
        case_id="CASE-900",
        alert={
            "severity": "high",
        },
    )


    assert (
        plan["case_id"]
        ==
        "CASE-900"
    )


    assert (
        len(plan["tasks"])
        ==
        4
    )



def test_critical_plan_priority():

    planner = InvestigationExecutionPlanner()


    plan = planner.create_plan(
        case_id="CASE-901",
        alert={
            "severity": "critical",
        },
    )


    assert (
        plan["tasks"][0]["name"]
        ==
        "urgent_triage"
    )



def test_plan_history():

    planner = InvestigationExecutionPlanner()


    planner.create_plan(
        case_id="CASE-902",
        alert={},
    )


    assert (
        len(
            planner.get_history()
        )
        ==
        1
    )



def test_clear_history():

    planner = InvestigationExecutionPlanner()


    planner.create_plan(
        case_id="CASE-903",
        alert={},
    )


    planner.clear_history()


    assert (
        planner.get_history()
        ==
        []
    )