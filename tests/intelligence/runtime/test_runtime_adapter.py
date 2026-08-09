"""
Runtime Adapter Tests
"""


from services.intelligence.runtime.integration import (
    RuntimeAdapter,
)



class FakeRuntimeService:


    def start_investigation(
        self,
        case_id,
        evidence,
    ):

        return {

            "case_id":
                case_id,

            "status":
                "completed",

            "evidence":
                evidence,

        }



def create_adapter():

    return RuntimeAdapter(

        runtime_service=
            FakeRuntimeService()

    )



def test_adapter_creation():

    adapter = create_adapter()

    assert (
        adapter.runtime_service
        is not None
    )



def test_alert_normalization():

    adapter = create_adapter()


    result = adapter.normalize_alert(

        {

            "id":
                "CASE-001",

            "indicator":
                "malicious-domain.xyz",

            "severity":
                "high",

            "source":
                "email",

        }

    )


    assert (
        result["case_id"]
        ==
        "CASE-001"
    )


    assert (
        result["evidence"][0]["value"]
        ==
        "malicious-domain.xyz"
    )



def test_process_alert():

    adapter = create_adapter()


    result = adapter.process_alert(

        {

            "case_id":
                "CASE-002",

            "indicator":
                "evil.com",

        }

    )


    assert (
        result["status"]
        ==
        "completed"
    )



def test_source_mapping():

    adapter = create_adapter()


    result = adapter.normalize_alert(

        {

            "case_id":
                "CASE-003",

            "source":
                "microsoft_sentinel",

        }

    )


    assert (
        result["evidence"][0]["type"]
        ==
        "source"
    )