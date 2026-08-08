from services.intelligence.investigation.agent_registry import (
    InvestigationAgentRegistry,
)



def fake_agent(context):

    return {}



def test_register_agent():

    registry = InvestigationAgentRegistry()


    agent = registry.register(
        "ioc_agent",
        "ioc_analysis",
        fake_agent,
    )


    assert (
        agent["name"]
        ==
        "ioc_agent"
    )



def test_get_agent():

    registry = InvestigationAgentRegistry()


    registry.register(
        "mitre_agent",
        "mitre_mapping",
        fake_agent,
    )


    assert (
        registry.get(
            "mitre_agent"
        )
        is not None
    )



def test_agent_exists():

    registry = InvestigationAgentRegistry()


    assert (
        registry.exists(
            "unknown"
        )
        is False
    )