"""
Sentinel DNA Agent Factory Tests
"""

from services.intelligence.investigation.agent_factory import (
    InvestigationAgentFactory,
)



def test_register_default_agents():

    factory = (
        InvestigationAgentFactory()
    )


    registry = (
        factory.register_default_agents()
    )


    agents = (
        registry.list_agents()
    )


    assert (
        len(agents)
        ==
        5
    )



def test_mitre_agent_registered():

    factory = (
        InvestigationAgentFactory()
    )


    registry = (
        factory.register_default_agents()
    )


    assert (
        registry.exists(
            "mitre_agent"
        )
        is True
    )



def test_risk_agent_registered():

    factory = (
        InvestigationAgentFactory()
    )


    registry = (
        factory.register_default_agents()
    )


    agent = registry.get(
        "risk_agent"
    )


    assert (
        agent["capability"]
        ==
        "risk_analysis"
    )