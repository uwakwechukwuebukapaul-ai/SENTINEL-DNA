from services.intelligence.decision.decision_engine import (
    DecisionEngine,
)



def test_decision_generation():

    engine = DecisionEngine()


    result = engine.analyze(
        {
            "results": [
                {},
                {},
                {},
                {},
            ]
        }
    )


    assert (
        "decision"
        in result
    )


    assert (
        "recommendation"
        in result
    )