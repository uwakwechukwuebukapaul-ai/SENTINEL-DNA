"""
Decision Intelligence Engine Tests
"""

from services.intelligence.decision import (
    DecisionEngine,
)


def test_decision_creation():

    engine = DecisionEngine()


    result = engine.decide(
        {
            "case_id": "CASE-001",

            "indicators": [
                {
                    "value": "evil.com",
                    "type": "domain",
                }
            ],

            "confidence": 0.9,
        }
    )


    assert (
        result["case_id"]
        ==
        "CASE-001"
    )


    assert (
        result["risk"]["severity"]
        ==
        "high"
    )


    assert (
        "recommended_actions"
        in result
    )


def test_critical_response():

    engine = DecisionEngine()


    result = engine.decide(
        {
            "case_id": "CASE-002",

            "indicators": [
                {
                    "value": "malware.exe",
                },
                {
                    "value": "evil-domain.com",
                },
                {
                    "value": "192.168.1.50",
                },
            ],

            "confidence": 0.95,
        }
    )


    assert (
        result["risk"]["severity"]
        ==
        "critical"
    )


    assert (
        result["risk"]["priority"]
        ==
        "immediate"
    )


    assert (
        "Isolate affected assets"
        in
        result["recommended_actions"]
    )


def test_low_risk_decision():

    engine = DecisionEngine()


    result = engine.decide(
        {
            "case_id": "CASE-003",

            "indicators": [],

            "confidence": 0.0,
        }
    )


    assert (
        result["risk"]["severity"]
        ==
        "low"
    )


    assert (
        result["risk"]["priority"]
        ==
        "monitor"
    )


def test_history_tracking():

    engine = DecisionEngine()


    engine.decide(
        {
            "case_id": "CASE-004",
            "indicators": [],
            "confidence": 0.1,
        }
    )


    history = engine.get_history()


    assert (
        len(history)
        ==
        1
    )


    assert (
        history[0]["case_id"]
        ==
        "CASE-004"
    )


def test_clear_history():

    engine = DecisionEngine()


    engine.decide(
        {
            "case_id": "CASE-005",
        }
    )


    engine.clear_history()


    assert (
        engine.get_history()
        ==
        []
    )