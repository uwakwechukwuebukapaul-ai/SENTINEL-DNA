"""
Intelligence Fusion Pipeline

Coordinates threat intelligence fusion workflow.

Flow:

Indicator
    |
    v
Normalization
    |
    v
Fusion Engine
    |
    v
Risk Intelligence Result
"""

from typing import Any



class IntelligencePipeline:
    """
    High-level intelligence fusion execution pipeline.
    """


    def __init__(
        self,
        fusion_engine,
    ):

        self.fusion_engine = (
            fusion_engine
        )

        self.status = "ready"



    def investigate(
        self,
        indicator: str,
        indicator_type: str | None = None,
    ):

        """
        Execute intelligence fusion.
        """

        self.status = "running"


        normalized = (
            self._normalize_indicator(
                indicator,
                indicator_type,
            )
        )


        result = (
            self.fusion_engine.fuse(
                normalized["value"],
                normalized["type"],
            )
        )


        self.status = "completed"


        return {

            "indicator":
                normalized["value"],


            "type":
                normalized["type"],


            "analysis":
                (

                    result.to_dict()

                    if hasattr(
                        result,
                        "to_dict",
                    )

                    else result

                ),

        }



    def execute(
        self,
        indicators: list[dict[str, Any]],
    ):

        """
        Execute multiple indicator analysis.
        """

        results = []


        for indicator in indicators:

            results.append(

                self.investigate(

                    indicator.get(
                        "value"
                    ),

                    indicator.get(
                        "type"
                    ),

                )

            )


        return results



    def _normalize_indicator(
        self,
        indicator: str,
        indicator_type: str | None,
    ):

        return {

            "value":
                indicator.strip()
                if isinstance(
                    indicator,
                    str,
                )
                else indicator,


            "type":
                indicator_type
                or "unknown",

        }



    def health(
        self,
    ):

        return {

            "component":
                "intelligence_pipeline",

            "status":
                self.status,

        }