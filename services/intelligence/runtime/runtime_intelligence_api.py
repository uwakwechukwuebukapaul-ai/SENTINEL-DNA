"""
Runtime Intelligence API

Application interface for
Sentinel DNA intelligence runtime.
"""



class RuntimeIntelligenceAPI:
    """
    Runtime intelligence API facade.
    """



    def __init__(
        self,
        runtime,
        metrics=None,
    ):

        self.runtime = runtime

        self.metrics = metrics



    def execute_investigation(
        self,
        signals,
        case_id=None,
    ):


        result = (

            self.runtime.execute(
                signals,
                case_id,
            )

        )


        if self.metrics:

            self.metrics.record_execution(
                result.get(
                    "success",
                    False,
                )
            )


        return result



    def get_status(
        self,
    ):

        return self.runtime.health()



    def get_metrics(
        self,
    ):

        if self.metrics:

            return self.metrics.summary()



        return {

            "metrics":
                "unavailable"

        }