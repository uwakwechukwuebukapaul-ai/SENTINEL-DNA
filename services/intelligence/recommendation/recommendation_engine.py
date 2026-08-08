"""
Sentinel DNA Investigation Recommendation Engine

Generates AI-assisted investigation recommendations.
"""

from __future__ import annotations

from typing import Any


class RecommendationEngine:
    """
    Generates recommended SOC actions.

    Current:
        Rule-based reasoning.

    Future:
        LLM reasoning.
        Graph intelligence.
        Reinforcement learning.
    """

    def __init__(self) -> None:

        self.history: list[
            dict[str, Any]
        ] = []


    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate investigation recommendations.
        """

        recommendations: list[str] = []


        severity = investigation.get(
            "severity",
            "low",
        )


        if severity in (
            "critical",
            "high",
        ):

            recommendations.append(
                "Contain affected assets"
            )

            recommendations.append(
                "IOC blocking"
            )


        if investigation.get(
            "credential_compromise"
        ):

            recommendations.append(
                "Reset affected credentials"
            )


        if investigation.get(
            "malware_detected"
        ):

            recommendations.append(
                "Perform endpoint investigation"
            )


        if not recommendations:

            recommendations.append(
                "Continue monitoring"
            )


        result = {
            "investigation_id": investigation.get(
                "id"
            ),
            "recommendations": recommendations,
        }


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return recommendation history.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:
        """
        Clear recommendation history.
        """

        self.history.clear()