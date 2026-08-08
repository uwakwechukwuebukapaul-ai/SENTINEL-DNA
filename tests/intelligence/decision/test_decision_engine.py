from services.intelligence.decision import (
    DecisionEngine,
)



def test_critical_decision():

    engine = DecisionEngine()


    result = engine.analyze(
        {
            "id": "INV-001",
            "severity": "critical",
        }
    )


    assert result["decision"] == "respond"



def test_high_decision():

    engine = DecisionEngine()


    result = engine.analyze(
        {
            "severity": "high",
        }
    )


    assert result["priority"] == "high"



def test_medium_decision():

    engine = DecisionEngine()


    result = engine.analyze(
        {
            "severity": "medium",
        }
    )


    assert result["decision"] == "review"



def test_low_decision():

    engine = DecisionEngine()


    result = engine.analyze({})


    assert result["decision"] == "monitor"



def test_history():

    engine = DecisionEngine()

    engine.analyze({})

    assert len(
        engine.get_history()
    ) == 1



def test_clear_history():

    engine = DecisionEngine()

    engine.analyze({})

    engine.clear_history()

    assert engine.get_history() == []