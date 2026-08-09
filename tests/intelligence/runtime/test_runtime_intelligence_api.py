"""
Runtime Intelligence API Tests
"""


from services.intelligence.runtime.runtime_intelligence_api import (
    RuntimeIntelligenceAPI,
)



class FakeRuntime:

    def execute(
        self,
        signals,
        case_id=None,
    ):

        return {

            "success":
                True,

            "case_id":
                case_id,

        }



    def health(
        self,
    ):

        return {

            "status":
                "running"

        }



class FakeMetrics:

    def record_execution(
        self,
        success,
    ):

        self.success = success



    def summary(
        self,
    ):

        return {

            "executions":
                1

        }



def test_execute_investigation():

    api = RuntimeIntelligenceAPI(
        FakeRuntime(),
        FakeMetrics(),
    )


    result = api.execute_investigation(

        [

            {

                "type":
                    "domain",

                "value":
                    "evil.com",

            }

        ],

        "CASE-001",

    )


    assert (
        result["success"]
        is True
    )



def test_runtime_status():

    api = RuntimeIntelligenceAPI(
        FakeRuntime()
    )


    result = api.get_status()


    assert (
        result["status"]
        ==
        "running"
    )