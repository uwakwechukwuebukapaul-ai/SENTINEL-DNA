"""
Sentinel DNA Investigation Executor Tests
"""

from services.intelligence.investigation.investigation_executor import (
    InvestigationExecutor,
)

from services.intelligence.investigation.agent_dispatcher import (
    InvestigationAgentDispatcher,
)



def fake_agent(context):

    return {
        "analysis": "completed"
    }



def test_execute_plan():

    dispatcher = (
        InvestigationAgentDispatcher()
    )


    dispatcher.register_agent(
        "ioc_analysis",
        fake_agent,
    )


    executor = InvestigationExecutor(
        dispatcher
    )


    result = executor.execute(
        {
            "case_id": "CASE-100",
            "tasks": [
                {
                    "name": "ioc_analysis",
                    "priority": 1,
                }
            ],
        },
        {},
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        len(result["findings"])
        ==
        1
    )



def test_execution_history():

    executor = InvestigationExecutor()


    executor.execute(
        {
            "case_id": "CASE-101",
            "tasks": [],
        },
        {},
    )


    assert (
        len(
            executor.get_history()
        )
        ==
        1
    )



def test_clear_history():

    executor = InvestigationExecutor()


    executor.execute(
        {
            "case_id": "CASE-102",
            "tasks": [],
        },
        {},
    )


    executor.clear_history()


    assert (
        executor.get_history()
        ==
        []
    )