"""
Sentinel DNA Decision Recommendation Tests
"""

from services.intelligence.decision.recommendation_engine import (
    RecommendationEngine,
)



def test_critical_recommendation():

    engine = RecommendationEngine()


    result = engine.recommend(
        "critical",
        95,
    )


    assert (
        result["action"]
        ==
        "contain"
    )



def test_high_risk_recommendation():

    engine = RecommendationEngine()


    result = engine.recommend(
        "high",
        70,
    )


    assert (
        result["action"]
        ==
        "escalate"
    )



def test_low_risk_recommendation():

    engine = RecommendationEngine()


    result = engine.recommend(
        "low",
        10,
    )


    assert (
        result["action"]
        ==
        "monitor"
    )