"""
Sentinel DNA Recommendation Engine.

Generates SOC response recommendations,
automation candidates, and analyst actions.

Designed for:

- AI investigation workflows
- SOAR preparation
- analyst decision support
"""

from __future__ import annotations

from typing import Any


class RecommendationEngine:
    """
    Enterprise recommendation intelligence engine.
    """


    def __init__(self) -> None:

        self.history: list[dict[str, Any]] = []



    def recommend(
        self,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate recommendations from decision context.
        """

        severity = (
            decision.get(
                "severity",
                "",
            )
            .lower()
        )


        classification = (
            decision.get(
                "classification",
                "",
            )
            .lower()
        )


        priority = decision.get(
            "priority",
            "P4",
        )


        recommendations: list[str] = []

        automation_candidates: list[str] = []



        #
        # Phishing response
        #

        if classification == "phishing":

            recommendations.extend(
                [
                    "Block malicious sender and domains.",
                    "Remove phishing emails.",
                    "Reset affected credentials.",
                ]
            )


            automation_candidates.extend(
                [
                    "IOC blocking",
                    "Email quarantine",
                    "Sender domain blocking",
                ]
            )



        #
        # Malware response
        #

        elif classification == "malware":

            recommendations.extend(
                [
                    "Isolate affected endpoint.",
                    "Collect malware samples.",
                    "Perform endpoint investigation.",
                ]
            )


            automation_candidates.extend(
                [
                    "Endpoint isolation",
                    "Malware hash blocking",
                ]
            )



        #
        # High severity generic threat
        #

        elif severity in (
            "critical",
            "high",
        ) or priority in (
            "P1",
            "P2",
        ):

            recommendations.extend(
                [
                    "IOC blocking",
                    "Investigate affected assets",
                    "Collect additional evidence",
                ]
            )


            automation_candidates.extend(
                [
                    "IOC blocking",
                    "Threat hunting execution",
                ]
            )



        #
        # Unknown / low confidence
        #

        else:

            recommendations.append(
                "Continue monitoring."
            )



        result = {

            "status":
                "completed",


            "recommendations":
                recommendations,


            "automation_candidates":
                automation_candidates,


            "priority":
                priority,


            "automation_ready":
                len(
                    automation_candidates
                ) > 0,


            "count":
                len(
                    recommendations
                ),
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

        return self.history.copy()



    def clear_history(
        self,
    ) -> None:
        """
        Clear recommendation history.
        """

        self.history.clear()