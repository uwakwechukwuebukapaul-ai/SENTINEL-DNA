"""
Sentinel DNA Investigation Intelligence Layer.

High-level intelligence orchestration layer.

Combines:

- artifact analysis
- IOC correlation
- threat reasoning
- intelligence enrichment
"""

from __future__ import annotations

from typing import Any

from services.intelligence.correlation.correlation_engine import (
    CorrelationEngine,
)


class InvestigationIntelligence:
    """
    Enterprise investigation intelligence coordinator.
    """

    def __init__(
        self,
        correlation_engine=None,
    ) -> None:

        self.correlation_engine = (
            correlation_engine
            or CorrelationEngine()
        )


    def analyze(
        self,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute intelligence pipeline.
        """

        indicators = []

        techniques = []


        for artifact in artifacts:

            artifact_type = artifact.get(
                "type"
            )


            if artifact_type == "ioc":

                indicators.append(
                    {
                        "ioc":
                            artifact.get(
                                "value"
                            )
                    }
                )


            elif artifact_type == "threat":

                techniques.append(
                    {
                        "technique":
                            artifact.get(
                                "value"
                            )
                    }
                )


        reasoning = {

            "artifact_count":
                len(artifacts),

            "classification":
                self._classify(
                    artifacts
                ),
        }


        correlation = (
            self.correlation_engine.correlate(
                case_id="INTELLIGENCE",
                indicators=indicators,
                techniques=techniques,
                reasoning=reasoning,
            )
        )


        return {

            "status":
                "completed",


            "indicators":
                indicators,


            "techniques":
                techniques,


            "correlation":
                self._serialize_correlation(
                    correlation
                ),


            "reasoning":
                {
                    "reasoning_status":
                        "completed",

                    "classification":
                        reasoning["classification"],

                    "artifact_count":
                        reasoning["artifact_count"],
                },


            "confidence":
                correlation.confidence,
        }



    def _serialize_correlation(
        self,
        correlation,
    ) -> dict[str, Any]:
        """
        Convert correlation object
        into API-safe response.
        """

        return {

            "status":
                "completed",

            "case_id":
                correlation.case_id,

            "indicators":
                correlation.indicators,

            "techniques":
                correlation.techniques,

            "attack_story":
                correlation.attack_story,

            "confidence":
                round(
                    correlation.confidence,
                    2,
                ),

            "metadata":
                correlation.metadata,
        }



    def _classify(
        self,
        artifacts: list[dict[str, Any]],
    ) -> str:


        values = [
            item.get(
                "value",
                "",
            )
            for item in artifacts
        ]


        joined = " ".join(
            values
        ).lower()


        if "phishing" in joined:

            return "phishing"


        if "malware" in joined:

            return "malware"


        return "unknown"