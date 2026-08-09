"""
Correlation Engine Tests.
"""


from services.intelligence.correlation import (
    CorrelationEngine,
)



def create_engine():

    return CorrelationEngine()



def test_basic_correlation():

    engine = create_engine()


    result = engine.correlate(

        case_id="CASE-100",

        indicators=[
            {
                "value":
                    "evil-login.xyz"
            }
        ],

        techniques=[
            {
                "technique_id":
                    "T1566"
            }
        ],
    )


    assert (
        result.case_id
        ==
        "CASE-100"
    )


    assert (
        len(result.indicators)
        ==
        1
    )


    assert (
        len(result.techniques)
        ==
        1
    )



def test_attack_story_generation():

    engine = create_engine()


    result = engine.correlate(

        case_id="CASE-200",

        indicators=[
            {
                "type":
                    "domain"
            }
        ],

        techniques=[
            {
                "name":
                    "Credential Access"
            }
        ],
    )


    assert (
        len(result.attack_story)
        >
        0
    )



def test_confidence_score():

    engine = create_engine()


    result = engine.correlate(

        case_id="CASE-300",

        indicators=[
            {
                "ioc":
                    "test.com"
            }
        ],

        techniques=[],

        reasoning={
            "classification":
                "phishing"
        },
    )


    assert (
        result.confidence
        ==
        0.6
    )



def test_export():

    engine = create_engine()


    result = engine.correlate(

        case_id="CASE-400",

        indicators=[],

        techniques=[],
    )


    exported = result.to_dict()


    assert (
        exported["case_id"]
        ==
        "CASE-400"
    )


    assert (
        "metadata"
        in exported
    )