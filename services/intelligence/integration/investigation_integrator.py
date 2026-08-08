"""
Sentinel DNA Investigation Integration Layer

Connects intelligence engines into one workflow.
"""

from __future__ import annotations

from typing import Any


class InvestigationIntegrator:
    """
    Coordinates investigation intelligence.

    Future:
        - Dependency injection
        - Event streaming
        - Async execution
        - Agent workflows
    """

    def __init__(
        self,
        decision_engine=None,
        recommendation_engine=None,
    ) -> None:

        self.decision_engine = decision_engine
        self.recommendation_engine = recommendation_engine

        self.history: list[
            dict[str, Any]
        ] = []


    def process(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute intelligence workflow.
        """

        result = {
            "investigation_id": investigation.get(
                "id"
            ),
        }


        if self.decision_engine:

            result["decision"] = (
                self.decision_engine.analyze(
                    investigation
                )
            )


        if self.recommendation_engine:

            result["recommendations"] = (
                self.recommendation_engine.generate(
                    investigation
                )
            )


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return integration history.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:

        self.history.clear()