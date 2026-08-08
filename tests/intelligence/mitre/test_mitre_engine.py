from services.intelligence.mitre.mitre_engine import (
    MitreEngine,
)


from services.intelligence.investigation.evidence.evidence_model import (
    Evidence,
)



def test_mitre_mapping():


    evidence = [

        Evidence(

            evidence_type="ioc",

            source="email",

            value="phishing malicious-domain",

            confidence=90,

        )

    ]


    engine = MitreEngine()


    result = engine.analyze(
        evidence
    )


    assert len(result) > 0


    assert result[0].technique_id == "T1566"