"""
Autonomous Investigator Agent Tests.
"""

from services.intelligence.agents.investigator_agent import (
    InvestigatorAgent,
)



def create_agent():

    return InvestigatorAgent()



def test_agent_initialization():

    agent = create_agent()


    assert agent is not None


    assert hasattr(
        agent,
        "investigate",
    )



def test_agent_runs_investigation():

    agent = create_agent()


    result = agent.investigate(
        {
            "id":
                "INV-001",

            "classification":
                "phishing",

            "severity":
                "high",
        }
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["investigation_id"]
        ==
        "INV-001"
    )



def test_agent_generates_decision():

    agent = create_agent()


    result = agent.investigate(
        {
            "id":
                "INV-002",

            "classification":
                "malware",

            "severity":
                "critical",
        }
    )


    assert (
        result["decision"]
        is not None
    )



def test_agent_requires_approval():

    agent = create_agent()


    result = agent.investigate(
        {
            "id":
                "INV-003",

            "classification":
                "malware",

            "severity":
                "critical",

            "requires_approval":
                True,
        }
    )


    assert (
        result["approval_required"]
        is True
    )