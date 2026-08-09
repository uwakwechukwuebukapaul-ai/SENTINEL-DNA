"""
Threat Fusion Engine Tests
"""


from services.intelligence.fusion import (
    ThreatFusionEngine,
)



def test_engine_creation():

    engine = ThreatFusionEngine()

    assert engine is not None



def test_critical_threat_fusion():

    engine = ThreatFusionEngine()


    result = engine.fuse(

        {

            "case_id":
                "CASE-001",

        },


        {

            "risk_score":
                90,

            "indicators":

                [

                    {

                        "type":
                            "domain",

                        "value":
                            "evil.com",

                        "confidence":
                            90,

                    }

                ],

        }

    )


    assert (
        result["threat_assessment"]["risk"]
        ==
        "critical"
    )


    assert (
        result["investigation_required"]
        is True
    )



def test_priority_generation():

    engine = ThreatFusionEngine()


    result = engine.fuse(

        {},

        {

            "risk_score":
                60,

            "indicators":
                [],

        }

    )


    assert (
        result["threat_assessment"]["priority"]
        ==
        "urgent"
    )



def test_confidence_calculation():

    engine = ThreatFusionEngine()


    result = engine.fuse(

        {},

        {

            "risk_score":
                90,

            "indicators":

                [

                    {
                        "confidence":
                            80,
                    },

                    {
                        "confidence":
                            100,
                    },

                ],

        }

    )


    assert (
        result["threat_assessment"]["confidence"]
        ==
        90
    )



def test_summary_generation():

    engine = ThreatFusionEngine()


    result = engine.fuse(

        {},

        {

            "risk_score":
                90,

            "indicators":
                [{}],

        }

    )


    assert (
        "Critical"
        in
        result["summary"]
    )