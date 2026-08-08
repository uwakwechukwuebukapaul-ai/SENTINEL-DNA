"""
Sentinel DNA Confidence Scoring Engine
"""

from __future__ import annotations

from typing import Any



class ConfidenceScoringEngine:
    """
    Calculates confidence of investigation decisions.
    """

    def calculate(
        self,
        evidence: list[dict[str, Any]],
    ) -> float:
        """
        Calculate confidence score.
        """

        if not evidence:
            return 0.0


        score = (
            len(evidence) * 20
        )


        return min(
            score,
            100.0,
        )