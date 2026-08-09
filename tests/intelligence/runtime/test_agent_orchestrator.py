"""
Tests for Sentinel DNA Agent Runtime.
"""

from services.intelligence.runtime.agent_registry import (
    AgentRegistry,
)

from services.intelligence.runtime.agent_orchestrator import (
    AgentOrchestrator,
)


from services.intelligence.agents.investigator_agent import (
    InvestigatorAgent,
)



def create_runtime():

    registry = AgentRegistry()


    registry.register(
        "investigator",
        InvestigatorAgent(),
    )


    return AgentOrchestrator(
        registry
    )



def test_agent_registration():

    registry = AgentRegistry()


    registry.register(
        "test",
        object(),
    )


    assert (
        "test"
        in registry.list_agents()
    )



def test_agent_execution():

    runtime = create_runtime()


    result = runtime.execute(
        "investigator",
        {
            "id":
                "INV-100",

            "severity":
                "critical",

            "classification":
                "malware",
        },
    )


    assert (
        result["status"]
        ==
        "completed"
    )



def test_execution_history():

    runtime = create_runtime()


    runtime.execute(
        "investigator",
        {
            "id":
                "INV-101",
        },
    )


    assert len(
        runtime.get_history()
    ) == 1



def test_clear_history():

    runtime = create_runtime()


    runtime.execute(
        "investigator",
        {},
    )


    runtime.clear_history()


    assert len(
        runtime.get_history()
    ) == 0