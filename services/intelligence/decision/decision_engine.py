"""
Sentinel DNA Autonomous Investigation Decision Engine

Central reasoning layer for investigation decisions.
"""

from __future__ import annotations

from typing import Any


class DecisionEngine:
    """
    Produces investigation decisions.

    Current:
        Rule-based decision logic.

    Future:
        LLM reasoning.
        Graph reasoning.
        Autonomous agent planning.
    """

    def __init__(self) -> None:

        self.history: list[
            dict[str, Any]
        ] = []


    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze investigation and produce decision.
        """

        severity = investigation.get(
            "severity",
            "low",
        )


        decision = "monitor"

        priority = "low"


        if severity == "critical":

            decision = "respond"

            priority = "critical"


        elif severity == "high":

            decision = "investigate"

            priority = "high"


        elif severity == "medium":

            decision = "review"

            priority = "medium"


        result = {
            "investigation_id": investigation.get(
                "id"
            ),
            "decision": decision,
            "priority": priority,
        }


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return decisions.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:
        """
        Clear decision history.
        """

        self.history.clear()