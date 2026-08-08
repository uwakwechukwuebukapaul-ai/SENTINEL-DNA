"""
Sentinel DNA Recommendation Engine

Generates explainable security response
recommendations from investigation context.
"""

from __future__ import annotations

from typing import Any


class RecommendationEngine:
    """
    Generates SOC investigation recommendations.
    """

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []


    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate recommendations from investigation data.
        """

        recommendations: list[str] = []

        severity = str(
            investigation.get(
                "severity",
                "",
            )
        ).lower()


        # High impact security incidents
        if severity in (
            "critical",
            "high",
        ):

            recommendations.extend(
                [
                    "Contain affected assets",
                    "IOC blocking",
                    "Escalate investigation",
                ]
            )


        # Credential compromise response
        if investigation.get(
            "credential_compromise"
        ):

            recommendations.append(
                "Reset affected credentials"
            )

            recommendations.append(
                "Review authentication activity"
            )


        # Malware indicators
        if investigation.get(
            "malware_detected"
        ):

            recommendations.append(
                "Isolate infected systems"
            )

            recommendations.append(
                "Perform malware analysis"
            )


        # Suspicious IOC activity
        if investigation.get(
            "ioc_detected"
        ):

            recommendations.append(
                "Block malicious indicators"
            )


        # Medium severity investigations
        if severity == "medium":

            recommendations.append(
                "Investigate further"
            )


        # Default action
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