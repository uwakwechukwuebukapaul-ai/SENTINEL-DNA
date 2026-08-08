"""
Sentinel DNA Recommendation Engine

Generates investigation response recommendations.
"""

from __future__ import annotations

from typing import Any


class RecommendationEngine:
    """
    Generates security investigation recommendations.
    """

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []


    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate recommendations from investigation context.
        """

        recommendations: list[str] = []


        severity = investigation.get(
            "severity",
            ""
        ).lower()


        # High severity response
        if severity == "high":

            recommendations.extend(
                [
                    "Contain affected assets",
                    "IOC blocking",
                ]
            )


        # Critical severity response
        elif severity == "critical":

            recommendations.extend(
                [
                    "Isolate affected systems",
                    "IOC blocking",
                    "Escalate incident",
                ]
            )


        # Credential compromise response
        if investigation.get(
            "credential_compromise",
            False,
        ):

            recommendations.append(
                "Reset affected credentials"
            )


        # Malware response
        if investigation.get(
            "malware_detected",
            False,
        ):

            recommendations.append(
                "Perform malware containment"
            )


        # IOC response
        if investigation.get(
            "ioc_detected",
            False,
        ):

            recommendations.append(
                "Block malicious indicators"
            )


        # Default recommendation
        if not recommendations:

            recommendations.append(
                "Continue monitoring"
            )


        result = {
            "recommendations": recommendations
        }


        self.history.append(result)


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