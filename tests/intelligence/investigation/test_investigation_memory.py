"""
Tests for Investigation Memory.
"""

from services.intelligence.investigation.memory import (
    InvestigationMemory,
)


def test_memory_creation():

    memory = InvestigationMemory(
        "INV-001"
    )

    assert (
        memory.investigation_id
        ==
        "INV-001"
    )



def test_add_finding():

    memory = InvestigationMemory(
        "INV-001"
    )


    memory.add_finding(
        {
            "type":
                "phishing"
        }
    )


    assert len(
        memory.findings
    ) == 1



def test_snapshot():

    memory = InvestigationMemory(
        "INV-001"
    )


    result = memory.snapshot()


    assert (
        result["investigation_id"]
        ==
        "INV-001"
    )