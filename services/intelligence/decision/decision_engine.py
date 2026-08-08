"""
Sentinel DNA Investigation Decision Engine
"""

from __future__ import annotations

from typing import Any

from .confidence_scoring import (
    ConfidenceScoringEngine,
)

from .recommendation_engine import (
    RecommendationEngine,
)



class DecisionEngine:
    """
    Converts investigation results into decisions.
    """

    def __init__(self) -> None:

        self.confidence_engine = (
            ConfidenceScoringEngine()
        )

        self.recommendation_engine = (
            RecommendationEngine()
        )


        self.history: list[
            dict[str, Any]
        ] = []



    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze investigation output.
        """

        results = investigation.get(
            "results",
            [],
        )


        confidence = (
            self.confidence_engine
            .calculate(results)
        )


        if confidence >= 80:

            decision = "critical"

        elif confidence >= 40:

            decision = "high"

        else:

            decision = "low"



        recommendation = (
            self.recommendation_engine
            .recommend(
                decision,
                int(confidence),
            )
        )


        result = {
            "decision": decision,
            "confidence": confidence,
            "recommendation":
                recommendation,
        }


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history