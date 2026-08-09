"""
Event Gateway Tests
"""


from services.intelligence.ingestion import (
    EventGateway,
    EventNormalizer,
)



class FakeAdapter:


    def process_alert(
        self,
        alert,
    ):

        return {

            "status":
                "completed",

            "case_id":
                alert["case_id"],

        }



def test_normalizer_creation():

    normalizer = EventNormalizer()

    assert normalizer is not None



def test_event_normalization():

    normalizer = EventNormalizer()


    result = normalizer.normalize(

        {

            "id":
                "CASE-001",

            "source":
                "splunk",

            "severity":
                "HIGH",

            "indicator":
                "malicious-domain.xyz",

        }

    )


    assert (
        result["case_id"]
        ==
        "CASE-001"
    )


    assert (
        result["severity"]
        ==
        "high"
    )


    assert (
        result["indicators"][0]
        ==
        "malicious-domain.xyz"
    )



def test_gateway_creation():

    gateway = EventGateway()

    assert gateway is not None



def test_gateway_ingestion():

    gateway = EventGateway(

        adapter=
            FakeAdapter()

    )


    result = gateway.ingest(

        {

            "case_id":
                "CASE-002",

            "source":
                "microsoft_sentinel",

            "severity":
                "high",

            "indicator":
                "evil.com",

        }

    )


    assert (
        result["status"]
        ==
        "completed"
    )


    assert (
        result["case_id"]
        ==
        "CASE-002"
    )