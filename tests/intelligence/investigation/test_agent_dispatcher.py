"""
Sentinel DNA Agent Dispatcher Tests
"""

from services.intelligence.investigation.agent_dispatcher import (
    InvestigationAgentDispatcher,
)



def fake_ioc_agent(context):

    return {
        "ioc_count": 3
    }



def test_register_agent():

    dispatcher = (
        InvestigationAgentDispatcher()
    )


    dispatcher.register_agent(
        "ioc_analysis",
        fake_ioc_agent,
    )


    assert (
        "ioc_analysis"
        in dispatcher.agents
    )



def test_dispatch_agent():

    dispatcher = (
        InvestigationAgentDispatcher()
    )


    dispatcher.register_agent(
        "ioc_analysis",
        fake_ioc_agent,
    )


    result = dispatcher.dispatch(
        "ioc_analysis",
        {},
    )


    assert (
        result["status"]
        ==
        "completed"
    )



def test_unknown_agent():

    dispatcher = (
        InvestigationAgentDispatcher()
    )


    result = dispatcher.dispatch(
        "unknown",
        {},
    )


    assert (
        result["status"]
        ==
        "failed"
    )



def test_dispatch_history():

    dispatcher = (
        InvestigationAgentDispatcher()
    )


    dispatcher.dispatch(
        "unknown",
        {},
    )


    assert (
        len(
            dispatcher.get_history()
        )
        ==
        1
    )