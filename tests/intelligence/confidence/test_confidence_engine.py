from services.intelligence.confidence import (
    ConfidenceEngine,
)



def test_high_confidence():

    engine = ConfidenceEngine()


    result = engine.calculate(
        {
            "severity": "critical",
            "credential_compromise": True,
            "ioc_detected": True,
        }
    )


    assert (
        result["confidence_level"]
        == "high"
    )



def test_medium_confidence():

    engine = ConfidenceEngine()


    result = engine.calculate(
        {}
    )


    assert (
        result["confidence_level"]
        == "medium"
    )



def test_confidence_history():

    engine = ConfidenceEngine()

    engine.calculate({})


    assert len(
        engine.get_history()
    ) == 1



def test_clear_history():

    engine = ConfidenceEngine()

    engine.calculate({})

    engine.clear_history()


    assert engine.get_history() == []