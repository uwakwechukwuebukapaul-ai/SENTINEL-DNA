"""
Sentinel DNA Recommendation Engine
"""

from __future__ import annotations

from typing import Any



class RecommendationEngine:
    """
    Generates SOC recommendations.
    """

    def recommend(
        self,
        decision: str,
        risk_score: int,
    ) -> dict[str, Any]:
        """
        Generate response recommendation.
        """

        if decision == "critical":

            return {
                "action": "contain",
                "priority": "high",
                "reason":
                    "Critical security risk detected",
            }


        if decision == "high":

            return {
                "action": "escalate",
                "priority": "medium",
                "reason":
                    "Requires analyst review",
            }


        return {
            "action": "monitor",
            "priority": "low",
            "reason":
                "Low security impact",
        }