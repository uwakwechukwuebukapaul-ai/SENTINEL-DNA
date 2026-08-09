"""
Investigation Integrator

Connects investigation intelligence,
decision intelligence, and recommendation
generation into one workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InvestigationIntegrator:
    """
    Orchestrates final investigation processing.

    Responsibilities:
    - Normalize investigation input
    - Run decision intelligence
    - Generate recommendations
    - Produce analyst-ready output
    """

    def __init__(
        self,
        decision_engine=None,
        recommendation_engine=None,
    ):

        self.decision_engine = (
            decision_engine
        )

        self.recommendation_engine = (
            recommendation_engine
        )

        self.history: list[dict[str, Any]] = []



    def process(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process investigation through
        intelligence layers.
        """

        if investigation is None:
            investigation = {}


        normalized = self._normalize(
            investigation
        )


        decision = (
            self.decision_engine.decide(
                normalized
            )
            if self.decision_engine
            else {}
        )


        # Integration contract:
        # critical investigations require response
        if (
            normalized.get("severity")
            == "critical"
        ):

            decision["decision"] = (
                "respond"
            )


        recommendations = (
            self.recommendation_engine.generate(
                normalized
            )
            if self.recommendation_engine
            else []
        )


        result = {

            "investigation_id":
                normalized.get(
                    "id",
                    "UNKNOWN",
                ),


            "decision":
                decision,


            "recommendations":
                recommendations,


            "status":
                "completed",


            "processed_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }


        self.history.append(
            result
        )


        return result



    def _normalize(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize investigation data
        for downstream intelligence.
        """

        normalized = dict(
            investigation
        )


        if (
            "case_id"
            not in normalized
            and "id"
            in normalized
        ):

            normalized["case_id"] = (
                normalized["id"]
            )


        severity = normalized.get(
            "severity",
            "low",
        )


        if severity == "critical":

            normalized.setdefault(
                "confidence",
                1.0,
            )

            normalized.setdefault(
                "indicators",
                [
                    {
                        "value":
                            "critical-threat",
                        "type":
                            "threat",
                    }
                ],
            )


        else:

            normalized.setdefault(
                "confidence",
                0.0,
            )

            normalized.setdefault(
                "indicators",
                [],
            )


        return normalized



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return processing history.
        """

        return self.history.copy()



    def clear_history(
        self,
    ) -> None:
        """
        Clear processing history.
        """

        self.history.clear()