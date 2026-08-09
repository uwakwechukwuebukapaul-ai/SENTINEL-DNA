"""
Runtime Service Tests

Validates service boundary.
"""


from services.intelligence.runtime.api.runtime_service import (
    RuntimeService,
)

from services.intelligence.runtime import (
    RuntimeResult,
)



class FakeRuntime:


    def execute(
        self,
        case_id,
        evidence,
    ):

        return RuntimeResult(

            case_id=case_id,

            status="completed",

            investigation={

                "analysis": {

                    "risk":
                        "high"

                }

            },

            execution={

                "action":
                    "contain"

            },

            report={

                "status":
                    "completed"

            },

        )



def create_service():

    return RuntimeService(
        runtime=FakeRuntime()
    )



def test_service_creation():

    service = create_service()

    assert service.runtime is not None



def test_start_investigation():

    service = create_service()


    result = service.start_investigation(

        case_id="CASE-001",

        evidence=[],

    )


    assert (
        result["status"]
        ==
        "completed"
    )



def test_service_investigation_result():

    service = create_service()


    result = service.start_investigation(

        case_id="CASE-002",

    )


    assert (
        result["investigation"]["analysis"]["risk"]
        ==
        "high"
    )



def test_service_execution_result():

    service = create_service()


    result = service.start_investigation(

        case_id="CASE-003",

    )


    assert (
        result["execution"]["action"]
        ==
        "contain"
    )



def test_service_report_result():

    service = create_service()


    result = service.start_investigation(

        case_id="CASE-004",

    )


    assert (
        result["report"]["status"]
        ==
        "completed"
    )



def test_missing_case_id():

    service = create_service()


    result = service.start_investigation(
        case_id=""
    )


    assert (
        result["status"]
        ==
        "failed"
    )