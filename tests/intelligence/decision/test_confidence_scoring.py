from services.intelligence.decision.confidence_scoring import (
    ConfidenceScoringEngine,
)



def test_confidence_score():

    engine = ConfidenceScoringEngine()


    score = engine.calculate(
        [
            {
                "ioc": "test"
            }
        ]
    )


    assert score == 20