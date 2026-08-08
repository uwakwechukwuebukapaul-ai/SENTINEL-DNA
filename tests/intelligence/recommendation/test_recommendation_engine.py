from services.intelligence.recommendation import (
    RecommendationEngine,
)


def test_high_risk_recommendation():

    engine = RecommendationEngine()


    result = engine.generate(
        {
            "id": "INV-001",
            "severity": "high",
        }
    )


    assert (
        "IOC blocking"
        in result["recommendations"]
    )



def test_credential_recommendation():

    engine = RecommendationEngine()


    result = engine.generate(
        {
            "credential_compromise": True,
        }
    )


    assert (
        "Reset affected credentials"
        in result["recommendations"]
    )



def test_low_risk_monitoring():

    engine = RecommendationEngine()


    result = engine.generate(
        {}
    )


    assert (
        "Continue monitoring"
        in result["recommendations"]
    )



def test_history():

    engine = RecommendationEngine()


    engine.generate(
        {
            "id": "INV-001"
        }
    )


    assert len(
        engine.get_history()
    ) == 1



def test_clear_history():

    engine = RecommendationEngine()


    engine.generate({})

    engine.clear_history()


    assert engine.get_history() == []