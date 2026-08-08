from services.intelligence.decision import (
    DecisionEngine,
)



def test_high_risk_decision():

    engine = DecisionEngine()


    result = engine.decide(
        {
            "id": "INC-001",
            "severity": "high",
        }
    )


    assert (
        result["decision"]
        == "respond_immediately"
    )



def test_medium_risk_decision():

    engine = DecisionEngine()


    result = engine.decide(
        {
            "severity": "medium",
        }
    )


    assert (
        result["decision"]
        == "investigate_further"
    )



def test_history():

    engine = DecisionEngine()

    engine.decide({})


    assert len(
        engine.get_history()
    ) == 1



def test_clear_history():

    engine = DecisionEngine()

    engine.decide({})

    engine.clear_history()


    assert engine.get_history() == []