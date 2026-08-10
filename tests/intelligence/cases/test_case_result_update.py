"""
Case Manager Investigation Result Tests.

Validates that investigation intelligence
is attached correctly to case lifecycle.
"""

from services.intelligence.cases.case_manager import (
    CaseManager,
)



def test_case_investigation_update():

    manager = CaseManager()


    manager.create_case(
        "CASE-001",
        {
            "source": "email",
            "alert_type": "phishing",
        },
    )


    investigation_result = {

        "investigation_id":
            "INV-001",


        "risk":
        {
            "level": "high",
            "score": 90,
        },


        "confidence":
            0.95,


        "findings":
        [
            "Credential phishing detected",
            "Suspicious authentication activity",
        ],


        "indicators":
        [
            "evil.com",
        ],


        "mitre":
        [
            "T1566",
        ],


        "timeline":
        [
            {
                "event":
                    "email_received",
            }
        ],


        "recommendations":
        [
            "Reset compromised credentials",
        ],


        "report":
        {
            "summary":
                "High risk phishing investigation",
        },

    }


    case = manager.update_investigation_result(
        "CASE-001",
        investigation_result,
    )


    assert (
        case["investigation_id"]
        ==
        "INV-001"
    )


    assert (
        case["risk"]["level"]
        ==
        "high"
    )


    assert (
        case["risk"]["score"]
        ==
        90
    )


    assert (
        case["confidence"]
        ==
        0.95
    )


    assert (
        case["findings"][0]
        ==
        "Credential phishing detected"
    )


    assert (
        case["indicators"][0]
        ==
        "evil.com"
    )


    assert (
        case["mitre"][0]
        ==
        "T1566"
    )


    assert (
        case["recommendations"][0]
        ==
        "Reset compromised credentials"
    )


    assert (
        case["report"]["summary"]
        ==
        "High risk phishing investigation"
    )



def test_case_investigation_update_missing_case():

    manager = CaseManager()


    try:

        manager.update_investigation_result(
            "CASE-NOT-FOUND",
            {},
        )

        assert False


    except ValueError as exc:

        assert (
            str(exc)
            ==
            "Case not found"
        )



def test_case_timeline_records_completion():

    manager = CaseManager()


    manager.create_case(
        "CASE-002",
        {
            "source": "endpoint",
        },
    )


    manager.update_investigation_result(
        "CASE-002",
        {
            "investigation_id":
                "INV-002",
        },
    )


    case = manager.get_case(
        "CASE-002"
    )


    events = case["timeline"].events


    assert any(
        event["type"]
        ==
        "investigation_completed"
        for event in events
    )