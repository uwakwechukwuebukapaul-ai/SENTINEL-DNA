"""
Threat Intelligence Tests
"""


from services.intelligence.threat_intelligence import (
    IOCExtractor,
    EnrichmentEngine,
)



def test_ioc_extractor():

    extractor = IOCExtractor()


    result = extractor.extract(

        {

            "domain":
                "malicious-domain.xyz",

            "ip":
                "10.10.10.10",

        }

    )


    assert len(result) == 2


    assert (
        result[0]["type"]
        ==
        "domain"
    )



def test_enrichment_creation():

    engine = EnrichmentEngine()

    assert engine is not None



def test_malicious_enrichment():

    engine = EnrichmentEngine()


    result = engine.enrich(

        {

            "case_id":
                "CASE-001",

            "source":
                "email",

            "domain":
                "malicious-domain.xyz",

        }

    )


    indicator = (
        result["indicators"][0]
    )


    assert (
        indicator["reputation"]
        ==
        "malicious"
    )


    assert (
        indicator["risk"]
        ==
        "critical"
    )



def test_attack_mapping():

    engine = EnrichmentEngine()


    result = engine.enrich(

        {

            "url":
                "http://phish.example",

        }

    )


    assert (
        "T1566"
        in
        result["indicators"][0]["attack_patterns"]
    )



def test_risk_score():

    engine = EnrichmentEngine()


    result = engine.enrich(

        {

            "indicator":
                "evil-domain.com",

        }

    )


    assert (
        result["risk_score"]
        >
        0
    )