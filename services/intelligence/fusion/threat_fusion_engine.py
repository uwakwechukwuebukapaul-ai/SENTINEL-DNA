"""
Sentinel DNA Threat Fusion Engine

Enterprise threat intelligence fusion layer.

Responsibilities:

- combine threat intelligence signals
- calculate threat severity
- generate investigation priority
- calculate confidence
- produce analyst-ready summaries
"""

from __future__ import annotations

from typing import Any


class ThreatFusionEngine:
    """
    Threat intelligence fusion engine.

    Combines:

    - risk scoring
    - IOC intelligence
    - confidence signals
    - investigation context
    """


    def __init__(self):
        pass


    def fuse(
        self,
        context: dict[str, Any] | None = None,
        intelligence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Fuse threat intelligence.

        Supports:

        fuse(intelligence)

        and:

        fuse(context, intelligence)

        for backward compatibility.
        """


        # Compatibility:
        # old callers pass only intelligence
        if intelligence is None:
            intelligence = context or {}
            context = {}



        risk_score = intelligence.get(
            "risk_score",
            0,
        )


        indicators = intelligence.get(
            "indicators",
            [],
        )



        #
        # Threat risk classification
        #

        if risk_score >= 90:

            risk = "critical"

        elif risk_score >= 70:

            risk = "high"

        elif risk_score >= 40:

            risk = "medium"

        else:

            risk = "low"



        #
        # Priority generation
        #

        if risk == "critical":

            priority = "critical"

        elif risk_score >= 60:

            priority = "urgent"

        elif risk == "high":

            priority = "high"

        else:

            priority = "normal"



        #
        # Confidence calculation
        #

        confidence_values = []


        for indicator in indicators:

            if isinstance(
                indicator,
                dict,
            ):

                confidence = indicator.get(
                    "confidence"
                )

                if confidence is not None:

                    confidence_values.append(
                        confidence
                    )



        if confidence_values:

            confidence = round(
                sum(confidence_values)
                /
                len(confidence_values)
            )

        else:

            confidence = risk_score



        #
        # Investigation decision
        #

        investigation_required = (
            risk_score >= 70
            or len(indicators) > 0
        )



        #
        # Summary
        #

        summary = (
            f"{risk.capitalize()} threat detected "
            f"with risk score {risk_score}"
        )



        #
        # Return contract
        #

        return {

            "case_id":
                context.get(
                    "case_id"
                )
                if context
                else None,


            "threat_assessment": {

                "risk":
                    risk,

                "priority":
                    priority,

                "confidence":
                    confidence,

                "risk_score":
                    risk_score,

            },


            "investigation_required":
                investigation_required,


            "summary":
                summary,


            "indicators":
                indicators,


            "metadata": {

                "context":
                    context or {},

            },

        }


# Compatibility aliases

FusionEngine = ThreatFusionEngine