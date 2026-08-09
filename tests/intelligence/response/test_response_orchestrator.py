"""
Sentinel DNA Response Orchestrator Tests.

Validates:

- response planning
- approval workflow
- execution workflow
- history management
"""

from services.intelligence.response.response_orchestrator import (
    ResponseOrchestrator,
)



def test_response_orchestrator_planning():

    engine = ResponseOrchestrator()


    result = engine.orchestrate(
        {
            "automation_candidates": [
                "IOC blocking",
                "Email quarantine",
            ]
        }
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert len(
        result["actions"]
    ) == 2



    assert (
        result["actions"][0]["name"]
        ==
        "IOC blocking"
    )



def test_high_risk_requires_approval():

    engine = ResponseOrchestrator()


    result = engine.orchestrate(
        {
            "automation_candidates": [
                "Endpoint isolation",
            ]
        }
    )


    assert (
        result["approval_required"]
        is True
    )



def test_safe_actions_execute():

    engine = ResponseOrchestrator()


    result = engine.orchestrate(
        {
            "automation_candidates": [
                "Email quarantine",
            ]
        }
    )


    assert (
        result["approval_required"]
        is False
    )


    assert (
        result["actions"][0]["status"]
        ==
        "executed"
    )



def test_history():

    engine = ResponseOrchestrator()


    engine.orchestrate(
        {
            "automation_candidates": [
                "IOC blocking",
            ]
        }
    )


    assert len(
        engine.get_history()
    ) == 1



def test_clear_history():

    engine = ResponseOrchestrator()


    engine.orchestrate(
        {}
    )


    engine.clear_history()


    assert len(
        engine.get_history()
    ) == 0