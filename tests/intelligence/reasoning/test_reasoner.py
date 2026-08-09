from services.intelligence.reasoning import (
    InvestigationReasoner,
)


class FakeResult:

    case_id = "CASE-900"

    findings = {

        "threat_intelligence": {

            "confidence": 0.9

        },

        "analysis_engine": {

            "confidence": 0.8

        }

    }



def test_reasoner():

    reasoner = InvestigationReasoner()


    report = reasoner.reason(
        FakeResult()
    )


    assert (
        report["case_id"]
        ==
        "CASE-900"
    )


    assert (
        report["threat_assessment"]
        ==
        "credential_phishing"
    )


    assert (
        report["confidence"]
        ==
        85.0
    )