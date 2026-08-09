"""
Sentinel DNA Priority Ranker.

Determines SOC incident priority
from threat context.
"""

from __future__ import annotations


class PriorityRanker:
    """
    Calculates incident response priority.
    """

    def rank(
        self,
        severity: str,
        confidence: float,
        classification: str,
    ) -> str:
        """
        Return priority level.
        """

        severity = severity.lower()


        if (
            severity == "critical"
            and confidence >= 0.8
        ):

            return "P1"


        if (
            severity == "high"
            and confidence >= 0.7
        ):

            return "P1"


        if (
            severity == "high"
            or confidence >= 0.6
        ):

            return "P2"


        if classification != "unknown":

            return "P3"


        return "P4"