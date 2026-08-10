"""
Confidence Analysis Engine.

Calculates confidence in reasoning decisions.
"""


class ConfidenceAnalyzer:


    def calculate(
        self,
        evidence: dict,
        hypothesis: dict,
    ) -> float:


        indicator_count = (
            evidence.get(
                "indicator_count",
                0,
            )
        )


        if indicator_count >= 5:
            return 0.95


        if indicator_count >= 2:
            return 0.80


        if indicator_count == 1:
            return 0.60


        return 0.20