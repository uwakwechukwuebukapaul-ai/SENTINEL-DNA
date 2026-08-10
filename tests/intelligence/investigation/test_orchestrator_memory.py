"""
Tests Investigation Memory integration.
"""

from services.intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)



def test_orchestrator_creates_memory():

    engine = InvestigationOrchestrator()


    result = engine.investigate(
        case_id="CASE-100"
    )


    assert (
        "memory"
        in result
    )


    assert (
        result["memory"]["investigation_id"]
        ==
        "INV-CASE-100"
    )



def test_memory_tracks_confidence():

    engine = InvestigationOrchestrator()


    result = engine.investigate(
        case_id="CASE-101"
    )


    assert (
        result["memory"]["confidence_history"]
        ==
        [0.9]
    )



def test_memory_store_contains_case():

    engine = InvestigationOrchestrator()


    engine.investigate(
        case_id="CASE-102"
    )


    assert (
        "CASE-102"
        in engine.memory_store
    )