"""
Sentinel DNA Investigation Orchestrator Tests
"""

from services.intelligence.investigation.orchestrator import (
    AutonomousInvestigationOrchestrator,
)



def test_execute_investigation():

    orchestrator = (
        AutonomousInvestigationOrchestrator()
    )


    result = (
        orchestrator.investigate(
            "CASE-001",
            {
                "severity": "high",
            },
        )
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



def test_investigation_plan_created():

    orchestrator = (
        AutonomousInvestigationOrchestrator()
    )


    result = (
        orchestrator.investigate(
            "CASE-002",
            {
                "severity": "critical",
            },
        )
    )


    assert (
        "plan"
        in result
    )



def test_execution_history():

    orchestrator = (
        AutonomousInvestigationOrchestrator()
    )


    orchestrator.investigate(
        "CASE-003",
        {},
    )


    assert (
        len(
            orchestrator.get_history()
        )
        ==
        1
    )



def test_clear_history():

    orchestrator = (
        AutonomousInvestigationOrchestrator()
    )


    orchestrator.investigate(
        "CASE-004",
        {},
    )


    orchestrator.clear_history()


    assert (
        orchestrator.get_history()
        ==
        []
    )