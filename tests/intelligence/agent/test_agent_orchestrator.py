"""
Agent Orchestrator Tests.
"""

from services.intelligence.agent.agent_orchestrator import (
    AgentOrchestrator,
)



class FakeCorrelation:

    def correlate(
        self,
        case_id,
        indicators,
        techniques,
    ):

        return {
            "case_id": case_id,
            "confidence": 0.9,
            "threat": "phishing",
        }



class FakePipeline:

    def execute(
        self,
        alert,
    ):

        return {
            "status": "completed",
            "steps": 3,
        }



class FakeDecision:

    def decide(
        self,
        context,
    ):

        return {
            "decision": "respond",
            "severity": "critical",
        }



def create_orchestrator():

    return AgentOrchestrator(
        correlation_engine=FakeCorrelation(),
        investigation_pipeline=FakePipeline(),
        decision_engine=FakeDecision(),
    )



def test_orchestrator_creation():

    engine = create_orchestrator()

    assert engine is not None



def test_full_investigation():

    engine = create_orchestrator()


    result = engine.investigate(
        {
            "case_id": "CASE-100",

            "indicators": [
                {
                    "value":
                    "evil.com"
                }
            ],

            "techniques": [],
        }
    )


    assert (
        result["case_id"]
        ==
        "CASE-100"
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["decision"]["decision"]
        ==
        "respond"
    )



def test_history():

    engine = create_orchestrator()


    engine.investigate(
        {
            "case_id":
            "CASE-200"
        }
    )


    history = (
        engine.get_history()
    )


    assert len(history) == 1



def test_clear_history():

    engine = create_orchestrator()


    engine.investigate(
        {
            "case_id":
            "CASE-300"
        }
    )


    engine.clear_history()


    assert (
        engine.get_history()
        ==
        []
    )