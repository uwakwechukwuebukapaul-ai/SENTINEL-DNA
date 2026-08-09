"""
Execution Engine Tests

Validates:
- execution creation
- IOC enrichment actions
- response actions
- history tracking
- serialization
"""

from services.intelligence.execution import (
    ExecutionEngine,
)



def create_engine():

    return ExecutionEngine()



def test_execution_creation():

    engine = create_engine()


    result = engine.execute(
        {
            "case_id":
                "CASE-001",
        }
    )


    assert (
        result["case_id"]
        ==
        "CASE-001"
    )


    assert (
        result["status"]
        ==
        "completed"
    )



def test_ioc_execution():

    engine = create_engine()


    result = engine.execute(
        {
            "case_id":
                "CASE-002",

            "correlation":
                {

                    "indicators":
                        [
                            "evil.com"
                        ],
                },
        }
    )


    assert (
        len(
            result["actions"]
        )
        ==
        1
    )


    assert (
        result["actions"][0]["type"]
        ==
        "ioc_enrichment"
    )


    assert (
        result["actions"][0]["target"]
        ==
        "evil.com"
    )



def test_response_execution():

    engine = create_engine()


    result = engine.execute(
        {
            "case_id":
                "CASE-003",

            "decision":
                {
                    "decision":
                        "respond"
                },
        }
    )


    assert (
        len(
            result["actions"]
        )
        ==
        1
    )


    assert (
        result["actions"][0]["type"]
        ==
        "containment"
    )



def test_monitor_execution():

    engine = create_engine()


    result = engine.execute(
        {
            "case_id":
                "CASE-004",

            "decision":
                {
                    "decision":
                        "monitor"
                },
        }
    )


    assert (
        "Continue monitoring activity"
        in
        result["recommendations"]
    )



def test_execution_history():

    engine = create_engine()


    engine.execute(
        {
            "case_id":
                "CASE-005"
        }
    )


    history = (
        engine.get_history()
    )


    assert (
        len(history)
        ==
        1
    )


    assert (
        history[0]["case_id"]
        ==
        "CASE-005"
    )



def test_clear_history():

    engine = create_engine()


    engine.execute(
        {
            "case_id":
                "CASE-006"
        }
    )


    engine.clear_history()


    assert (
        len(
            engine.get_history()
        )
        ==
        0
    )



def test_execution_serialization():

    engine = create_engine()


    result = engine.execute(
        {
            "case_id":
                "CASE-007"
        }
    )


    assert (
        "created_at"
        in
        result
    )



def test_multiple_actions():

    engine = create_engine()


    result = engine.execute(
        {
            "case_id":
                "CASE-008",

            "correlation":
                {
                    "indicators":
                        [
                            "evil.com",
                            "bad-domain.xyz",
                        ],
                },

            "decision":
                {
                    "decision":
                        "respond"
                },
        }
    )


    assert (
        len(
            result["actions"]
        )
        ==
        3
    )



def test_empty_execution():

    engine = create_engine()


    result = engine.execute(
        {}
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["actions"]
        ==
        []
    )