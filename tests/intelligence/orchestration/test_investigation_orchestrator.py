"""
Investigation Orchestrator Tests

Validates orchestration of:
- investigation execution
- execution state
- agent coordination
- intelligence workflow
"""


from services.intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)


class FakeAgent:

    def __init__(self):
        self.name = "fake_investigator"

    def investigate(self, investigation):
        return {
            "agent": self.name,
            "findings": [
                "Suspicious activity detected"
            ],
        }


def test_orchestrator_creation():

    orchestrator = InvestigationOrchestrator()

    assert orchestrator is not None


def test_register_agent():

    orchestrator = InvestigationOrchestrator()

    agent = FakeAgent()

    orchestrator.register_agent(agent)

    assert (
        "fake_investigator"
        in orchestrator.agents
    )


def test_execute_investigation():

    orchestrator = InvestigationOrchestrator()

    orchestrator.register_agent(
        FakeAgent()
    )


    result = orchestrator.execute(
        {
            "id": "INV-001",
            "severity": "critical",
        }
    )


    assert (
        result["investigation_id"]
        == "INV-001"
    )


    assert (
        len(result["findings"])
        > 0
    )


def test_execution_state_created():

    orchestrator = InvestigationOrchestrator()


    result = orchestrator.execute(
        {
            "id": "INV-002",
            "severity": "high",
        }
    )


    assert (
        result["state"]["status"]
        == "completed"
    )


def test_investigation_history():

    orchestrator = InvestigationOrchestrator()


    orchestrator.execute(
        {
            "id": "INV-003",
        }
    )


    history = (
        orchestrator.get_history()
    )


    assert len(history) == 1


def test_clear_history():

    orchestrator = InvestigationOrchestrator()


    orchestrator.execute(
        {
            "id": "INV-004",
        }
    )


    orchestrator.clear_history()


    assert (
        len(
            orchestrator.get_history()
        )
        == 0
    )