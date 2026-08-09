"""
Runtime Intelligence Pipeline

Coordinates intelligence execution stages.

Flow:

Signals
   |
   v
Runtime Intelligence Runtime
   |
   v
Providers
   |
   v
Correlation
   |
   v
Fusion
   |
   v
Intelligence Result
"""

from typing import Any


from services.intelligence.runtime.runtime_intelligence_runtime import (
    RuntimeIntelligenceRuntime,
)



class RuntimeIntelligencePipeline:
    """
    Main intelligence execution pipeline.
    """


    def __init__(
        self,
        runtime: RuntimeIntelligenceRuntime,
    ):

        self.runtime = runtime


        self.stages = [
            "collection",
            "enrichment",
            "correlation",
            "fusion",
            "decision",
        ]



    def execute(
        self,
        signals: list[dict[str, Any]],
        case_id: str | None = None,
    ):


        result = (
            self.runtime.execute(
                signals,
                case_id,
            )
        )


        return result



    def describe(
        self,
    ):

        return {

            "pipeline":
                "runtime_intelligence_pipeline",

            "stages":
                self.stages,

        }