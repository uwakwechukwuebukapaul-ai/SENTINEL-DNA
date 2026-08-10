from services.intelligence.reasoning import (
    InvestigationReasoningEngine,
)


class FakeContext:

    artifacts = [
        {
            "url":
            "http://evil-login.com"
        }
    ]


def test_reasoning_engine():

    engine = InvestigationReasoningEngine()


    result = engine.reason(
        FakeContext()
    )


    assert (
        result["threat"]
        ==
        "credential_phishing"
    )


    assert (
        result["risk"]["confidence"]
        >
        0
    )