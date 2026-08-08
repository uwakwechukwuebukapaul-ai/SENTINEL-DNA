from services.intelligence.similarity import (
    SimilarityEngine,
)


def test_register_investigation():

    engine = SimilarityEngine()

    result = engine.register_investigation(
        {
            "id": "INV-001"
        }
    )

    assert result["id"] == "INV-001"



def test_compare_similarity():

    engine = SimilarityEngine()


    engine.register_investigation(
        {
            "iocs": [
                "malware.com"
            ],
            "techniques": [
                "T1566"
            ],
        }
    )


    result = engine.compare(
        {
            "iocs": [
                "malware.com"
            ],
            "techniques": [
                "T1566"
            ],
        }
    )


    assert result[0]["similarity_score"] == 100



def test_no_similarity():

    engine = SimilarityEngine()


    engine.register_investigation(
        {
            "iocs": [
                "bad.com"
            ],
        }
    )


    result = engine.compare(
        {
            "iocs": [
                "safe.com"
            ],
        }
    )


    assert result[0]["similarity_score"] == 0



def test_clear_history():

    engine = SimilarityEngine()

    engine.register_investigation({})

    engine.clear_history()

    assert engine.history == []