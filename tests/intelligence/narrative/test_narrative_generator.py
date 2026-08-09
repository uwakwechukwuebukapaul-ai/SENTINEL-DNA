"""
Sentinel DNA Narrative Generator Tests.

Validates AI investigation narrative generation.
"""

from services.intelligence.narrative.narrative_generator import (
    NarrativeGenerator,
)


def create_generator():

    return NarrativeGenerator()



def test_generate_phishing_narrative():

    generator = create_generator()


    intelligence = {

        "indicators": [

            {
                "ioc":
                    "malicious-domain.xyz"
            }

        ],


        "techniques": [

            {
                "technique":
                    "phishing"
            }

        ],


        "reasoning": {

            "reasoning_status":
                "completed",

            "classification":
                "phishing",

            "artifact_count":
                2,
        },


        "correlation": {

            "status":
                "completed",

            "case_id":
                "INTELLIGENCE",

        },


        "confidence":
            0.9,
    }


    result = generator.generate(
        intelligence
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["severity"]
        ==
        "high"
    )


    assert (
        result["attack_stage"]
        ==
        "Initial Access"
    )


    assert (
        "phishing"
        in result["summary"].lower()
    )


    assert (
        len(
            result["findings"]
        )
        >
        0
    )


    assert (
        len(
            result["recommendations"]
        )
        >
        0
    )



def test_generate_malware_narrative():

    generator = create_generator()


    result = generator.generate(

        {

            "reasoning": {

                "classification":
                    "malware",

                "reasoning_status":
                    "completed",

            },


            "confidence":
                0.85,


            "indicators":
                [
                    {
                        "ioc":
                            "evil.exe"
                    }
                ],


            "correlation":
                {
                    "status":
                        "completed"
                },
        }
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["attack_stage"]
        ==
        "Execution"
    )


    assert (
        result["severity"]
        ==
        "high"
    )


    assert (
        "malware"
        in result["summary"].lower()
    )



def test_generate_unknown_narrative():

    generator = create_generator()


    result = generator.generate(

        {

            "reasoning": {

                "classification":
                    "unknown",

            },


            "confidence":
                0.2,


            "correlation":
                {},
        }
    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["severity"]
        ==
        "low"
    )


    assert (
        result["attack_stage"]
        ==
        "Unknown"
    )


    assert (
        len(
            result["recommendations"]
        )
        >
        0
    )



def test_narrative_contains_correlation():

    generator = create_generator()


    correlation = {

        "status":
            "completed",

        "case_id":
            "CASE-100",

    }


    result = generator.generate(

        {

            "reasoning":
                {
                    "classification":
                        "phishing"
                },

            "confidence":
                0.7,

            "correlation":
                correlation,

        }
    )


    assert (
        result["correlation"]
        ==
        correlation
    )