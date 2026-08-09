"""
Tests for Sentinel DNA Decision Engine.
"""

from services.intelligence.decision.decision_engine import (
    DecisionEngine,
)


def create_engine():

    return DecisionEngine()



def test_decision_engine_phishing():

    engine = create_engine()


    result = engine.decide(

        {
            "classification":
                "phishing",

            "severity":
                "high",

            "confidence":
                0.9,
        }

    )


    assert result["status"] == "completed"

    assert result["priority"] == "P1"

    assert (
        "Block malicious sender and domains."
        in result["recommended_actions"]
    )



def test_decision_engine_malware():

    engine = create_engine()


    result = engine.decide(

        {
            "classification":
                "malware",

            "severity":
                "medium",

            "confidence":
                0.7,
        }

    )


    assert result["status"] == "completed"

    assert (
        "Isolate affected endpoint."
        in result["recommended_actions"]
    )



def test_decision_engine_unknown():

    engine = create_engine()


    result = engine.decide(

        {
            "classification":
                "unknown",

            "severity":
                "low",

            "confidence":
                0.2,
        }

    )


    assert result["priority"] == "P4"



def test_automation_flag():

    engine = create_engine()


    result = engine.decide(

        {
            "classification":
                "phishing",

            "severity":
                "medium",

            "confidence":
                0.5,
        }

    )


    assert (
        result["automation_ready"]
        is True
    )