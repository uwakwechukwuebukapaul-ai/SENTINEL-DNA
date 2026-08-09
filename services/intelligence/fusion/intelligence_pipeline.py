"""
Intelligence Pipeline

High-level intelligence workflow.

Coordinates:

- intelligence providers
- correlation engine
- fusion engine
- final intelligence output
"""

from typing import Any



class IntelligencePipeline:
    """
    Executes threat intelligence analysis workflow.
    """


    def __init__(
        self,
        providers=None,
        correlation_engine=None,
        fusion_engine=None,
    ):

        self.providers = (
            providers or []
        )

        self.correlation_engine = (
            correlation_engine
        )

        self.fusion_engine = (
            fusion_engine
        )



    def investigate(
        self,
        signals: list[dict[str, Any]],
        context=None,
    ):

        """
        Execute complete intelligence pipeline.
        """

        intelligence_records = []


        #
        # Provider enrichment
        #

        for provider in self.providers:

            records = provider.enrich(
                signals
            )

            intelligence_records.extend(
                records
            )



        #
        # Correlation
        #

        correlation = None


        if self.correlation_engine:

            correlation = (
                self.correlation_engine.correlate(
                    signals
                )
            )



        #
        # Fusion
        #

        fusion_result = None


        if self.fusion_engine:

            fusion_result = (
                self.fusion_engine.fuse(
                    {
                        "signals":
                            signals,

                        "records":
                            intelligence_records,

                        "correlation":
                            correlation,

                    }
                )
            )



        return {

            "signals":
                signals,

            "intelligence_records":
                intelligence_records,

            "correlation":
                correlation,

            "fusion":
                fusion_result,

            "success":
                True,

        }