"""
Investigation Report Tests.
"""

from services.intelligence.reporting import (
    InvestigationReport,
)


def create_report():

    return InvestigationReport()



def test_report_creation():

    reporter = create_report()

    assert reporter is not None



def test_generate_report():

    reporter = create_report()


    result = reporter.generate(
        {
            "case_id": "CASE-001",

            "correlation": {
                "confidence": 0.95,

                "attack_story":
                    "Phishing attack detected",

                "indicators": [
                    "evil.com"
                ],

                "techniques": [
                    "T1566"
                ],
            },

            "decision": {
                "decision":
                    "respond",
            },
        }
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


    assert (
        result["risk_rating"]
        ==
        "critical"
    )



def test_attack_story():

    reporter = create_report()


    result = reporter.generate(
        {
            "case_id": "CASE-002",

            "correlation": {
                "attack_story":
                    "Credential theft",
            },
        }
    )


    assert (
        result["attack_story"]
        ==
        "Credential theft"
    )



def test_history():

    reporter = create_report()


    reporter.generate(
        {
            "case_id":
                "CASE-003"
        }
    )


    assert len(
        reporter.get_history()
    ) == 1



def test_clear_history():

    reporter = create_report()


    reporter.generate(
        {
            "case_id":
                "CASE-004"
        }
    )


    reporter.clear_history()


    assert (
        reporter.get_history()
        ==
        []
    )