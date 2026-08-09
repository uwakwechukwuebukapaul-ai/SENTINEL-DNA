"""
Sentinel DNA - Threat Fusion Engine

Transforms enriched intelligence into
investigation decision context.
"""

from __future__ import annotations

from typing import Any



class ThreatFusionEngine:
    """
    Fuses multiple intelligence signals
    into a unified threat assessment.
    """



    def fuse(
        self,
        event: dict[str, Any],
        intelligence: dict[str, Any],
        reasoning: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate unified threat context.
        """


        indicators = (
            intelligence.get(
                "indicators",
                [],
            )
        )


        risk_score = (
            intelligence.get(
                "risk_score",
                0,
            )
        )


        risk_level = (
            self._calculate_risk_level(
                risk_score
            )
        )


        priority = (
            self._calculate_priority(
                risk_level
            )
        )


        return {

            "case_id":
                event.get(
                    "case_id",
                    "UNKNOWN",
                ),


            "threat_assessment": {

                "risk":
                    risk_level,

                "risk_score":
                    risk_score,

                "priority":
                    priority,

                "confidence":
                    self._confidence(
                        indicators
                    ),

            },


            "intelligence":

                intelligence,


            "reasoning":

                reasoning or {},


            "investigation_required":

                risk_level
                in
                [
                    "high",
                    "critical",
                ],


            "summary":

                self._generate_summary(
                    risk_level,
                    indicators,
                ),

        }



    def _calculate_risk_level(
        self,
        score: int,
    ) -> str:

        if score >= 90:

            return "critical"


        if score >= 50:

            return "high"


        if score >= 20:

            return "medium"


        return "low"



    def _calculate_priority(
        self,
        risk: str,
    ) -> str:

        priorities = {

            "critical":
                "immediate",

            "high":
                "urgent",

            "medium":
                "normal",

            "low":
                "low",

        }


        return priorities.get(
            risk,
            "normal",
        )



    def _confidence(
        self,
        indicators: list[dict[str, Any]],
    ) -> int:

        if not indicators:

            return 0


        values = []


        for indicator in indicators:

            values.append(

                indicator.get(
                    "confidence",
                    0,
                )

            )


        return int(
            sum(values)
            /
            len(values)
        )



    def _generate_summary(
        self,
        risk: str,
        indicators: list[dict[str, Any]],
    ) -> str:

        count = len(
            indicators
        )


        if risk == "critical":

            return (
                f"Critical threat detected "
                f"with {count} suspicious indicators"
            )


        if risk == "high":

            return (
                f"High risk activity detected "
                f"with {count} indicators"
            )


        return (
            "No significant threat detected"
        )