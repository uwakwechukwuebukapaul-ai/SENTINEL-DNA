"""
Sentinel DNA Confidence Engine

Calculates confidence level for AI decisions.
"""

from __future__ import annotations

from typing import Any


class ConfidenceEngine:
    """
    Evaluates confidence in investigation decisions.
    """

    def __init__(self):

        self.history: list[
            dict[str, Any]
        ] = []


    def calculate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calculate confidence score.
        """

        score = 50
        reasons = []


        if investigation.get(
            "severity"
        ) in (
            "high",
            "critical",
        ):

            score += 20

            reasons.append(
                "High severity indicator detected"
            )


        if investigation.get(
            "credential_compromise",
            False,
        ):

            score += 20

            reasons.append(
                "Credential compromise evidence found"
            )


        if investigation.get(
            "ioc_detected",
            False,
        ):

            score += 10

            reasons.append(
                "IOC evidence available"
            )


        if score > 100:
            score = 100


        result = {
            "confidence_score": score,
            "confidence_level": self._level(
                score
            ),
            "reasons": reasons,
        }


        self.history.append(
            result
        )


        return result



    def _level(
        self,
        score: int,
    ) -> str:

        if score >= 80:
            return "high"

        if score >= 50:
            return "medium"

        return "low"



    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history



    def clear_history(
        self,
    ) -> None:

        self.history.clear()