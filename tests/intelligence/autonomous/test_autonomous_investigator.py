"""
Autonomous Investigator Tests

Validates autonomous investigation workflow,
state transitions, memory handling, and execution.
"""

from services.intelligence.autonomous import (
    AutonomousInvestigator,
    InvestigationState,
    InvestigationMemory,
)


class FakePipeline:

    def execute(self, artifacts):

        return {
            "status": "completed",
            "analysis": {
                "risk": "high",
                "confidence": 0.9,
            },
            "artifacts": artifacts,
        }


class FakeDecisionEngine:

    def decide(self, result):

        return {
            "decision": "respond",
            "priority": "high",
        }


def create_investigator():

    return AutonomousInvestigator(
        pipeline=FakePipeline(),
        decision_engine=FakeDecisionEngine(),
    )


def test_investigator_initialization():

    investigator = create_investigator()

    assert investigator is not None

    assert isinstance(
        investigator.state,
        InvestigationState,
    )


def test_investigation_start():

    investigator = create_investigator()

    result = investigator.investigate(
        case_id="CASE-001",
        artifacts=[
            {
                "type": "ioc",
                "value": "evil.com",
            }
        ],
    )


    assert (
        result["case_id"]
        ==
        "CASE-001"
    )


    assert (
        result["status"]
        ==
        "completed"
    )


def test_pipeline_execution():

    investigator = create_investigator()


    result = investigator.investigate(
        case_id="CASE-002",
        artifacts=[
            {
                "type": "threat",
                "value": "phishing",
            }
        ],
    )


    assert (
        "analysis"
        in result
    )


def test_decision_generation():

    investigator = create_investigator()


    result = investigator.investigate(
        case_id="CASE-003",
        artifacts=[
            {
                "type": "ioc",
                "value": "malicious.xyz",
            }
        ],
    )


    assert (
        result["decision"]["decision"]
        ==
        "respond"
    )


def test_memory_tracking():

    investigator = create_investigator()


    investigator.investigate(
        case_id="CASE-004",
        artifacts=[],
    )


    memory = investigator.memory.get_history()


    assert (
        len(memory)
        ==
        1
    )


def test_multiple_investigations():

    investigator = create_investigator()


    investigator.investigate(
        case_id="CASE-A",
        artifacts=[],
    )


    investigator.investigate(
        case_id="CASE-B",
        artifacts=[],
    )


    history = (
        investigator.memory.get_history()
    )


    assert (
        len(history)
        ==
        2
    )


def test_memory_clear():

    memory = InvestigationMemory()


    memory.add(
        {
            "case_id": "CASE-001"
        }
    )


    memory.clear()


    assert (
        memory.get_history()
        ==
        []
    )


def test_state_completion():

    state = InvestigationState()


    state.complete()


    assert (
        state.status
        ==
        "completed"
    )


def test_state_failure():

    state = InvestigationState()


    state.fail(
        "error"
    )


    assert (
        state.status
        ==
        "failed"
    )