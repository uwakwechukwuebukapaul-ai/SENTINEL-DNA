"""
Tests for Sentinel DNA Recommendation Engine.
"""

from services.intelligence.decision.recommendation_engine import (
    RecommendationEngine,
)



def create_engine():

    return RecommendationEngine()



def test_phishing_recommendation():

    engine = create_engine()


    result = engine.recommend(

        {
            "classification": "phishing",
            "priority": "P1",
        }

    )


    assert result["status"] == "completed"


    assert (
        "Block malicious sender and domains."
        in result["recommendations"]
    )



def test_malware_recommendation():

    engine = create_engine()


    result = engine.recommend(

        {
            "classification": "malware",
            "priority": "P2",
        }

    )


    assert (
        "Isolate affected endpoint."
        in result["recommendations"]
    )



def test_automation_candidates():

    engine = create_engine()


    result = engine.recommend(

        {
            "classification": "phishing",
            "priority": "P1",
        }

    )


    assert (
        len(result["automation_candidates"])
        > 0
    )



def test_unknown_recommendation():

    engine = create_engine()


    result = engine.recommend(

        {
            "classification": "unknown",
            "priority": "P4",
        }

    )


    assert result["status"] == "completed"


    assert (
        "Continue monitoring."
        in result["recommendations"]
    )