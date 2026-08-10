"""
Tests for Sentinel DNA Investigation Context.
"""

try:
    from services.intelligence.investigation.context import (  # type: ignore[import-not-found]
        InvestigationContext,
    )
except ModuleNotFoundError:
    from src.services.intelligence.investigation.context import (  # type: ignore[import-not-found]
        InvestigationContext,
    )


def test_context_creation():

    context = InvestigationContext(
        case_id="CASE-001"
    )

    assert context.case_id == "CASE-001"

    assert context.status == "created"

    assert context.artifacts == []

    assert context.timeline == []



def test_context_add_event():

    context = InvestigationContext(
        case_id="CASE-001"
    )


    context.add_event(
        {
            "stage": "started",
            "message": "Investigation started",
        }
    )


    assert len(
        context.timeline
    ) == 1


    assert (
        context.timeline[0]["stage"]
        ==
        "started"
    )



def test_context_add_evidence():

    context = InvestigationContext(
        case_id="CASE-001"
    )


    context.add_evidence(
        {
            "type": "ioc",
            "value": "evil.com",
        }
    )


    assert len(
        context.evidence
    ) == 1



def test_context_intelligence_update():

    context = InvestigationContext(
        case_id="CASE-001"
    )


    context.set_intelligence(
        {
            "risk": "high",
        }
    )


    assert (
        context.intelligence["risk"]
        ==
        "high"
    )



def test_context_decisions_and_actions():

    context = InvestigationContext(
        case_id="CASE-001"
    )


    context.add_decision(
        {
            "decision":
                "contain",
        }
    )


    context.add_action(
        {
            "action":
                "disable_account",
        }
    )


    assert len(
        context.decisions
    ) == 1


    assert len(
        context.actions
    ) == 1



def test_context_complete():

    context = InvestigationContext(
        case_id="CASE-001"
    )


    context.complete()


    assert (
        context.status
        ==
        "completed"
    )



def test_context_fail():

    context = InvestigationContext(
        case_id="CASE-001"
    )


    context.fail()


    assert (
        context.status
        ==
        "failed"
    )



def test_context_to_dict():

    context = InvestigationContext(
        case_id="CASE-001",
        investigation_id="INV-001",
    )


    result = context.to_dict()


    assert (
        result["case_id"]
        ==
        "CASE-001"
    )


    assert (
        result["investigation_id"]
        ==
        "INV-001"
    )


    assert (
        result["status"]
        ==
        "created"
    )