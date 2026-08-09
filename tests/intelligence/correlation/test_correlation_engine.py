"""
Correlation Engine Tests
"""

from services.intelligence.correlation import (
    CorrelationEngine,
    EntityGraph,
)



def test_entity_graph_creation():

    graph = EntityGraph()

    assert graph is not None



def test_entity_addition():

    graph = EntityGraph()


    entity = graph.add_entity(

        "domain",

        "evil.com",

    )


    assert (
        entity["value"]
        ==
        "evil.com"
    )



def test_correlation_creation():

    engine = CorrelationEngine()

    assert engine is not None



def test_phishing_correlation():

    engine = CorrelationEngine()


    result = engine.correlate(

        [

            {

                "type":
                    "email",

                "value":
                    "phishing_email",

            },

            {

                "type":
                    "domain",

                "value":
                    "evil.com",

            },

        ]

    )


    assert (
        result["attack_pattern"]
        ==
        "credential_phishing"
    )


    assert (
        "T1566"
        in
        result["mitre"]
    )



def test_high_confidence_correlation():

    engine = CorrelationEngine()


    result = engine.correlate(

        [

            {
                "type":
                    "email",

                "value":
                    "mail",

            },

            {
                "type":
                    "domain",

                "value":
                    "evil.com",

            },

            {
                "type":
                    "user",

                "value":
                    "john",

            },

            {
                "type":
                    "ip",

                "value":
                    "10.0.0.1",

            },

        ]

    )


    assert (
        result["confidence"]
        >=
        0.8
    )


    assert (
        result["risk"]
        ==
        "high"
    )