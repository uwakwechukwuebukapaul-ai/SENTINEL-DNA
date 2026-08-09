"""
Sentinel DNA Investigation Integrator

Connects investigation intelligence components:
- decision engine
- recommendation engine
- investigation workflow history
"""

from __future__ import annotations

from typing import Any


class InvestigationIntegrator:
    """
    Coordinates investigation intelligence workflow.
    """


    def __init__(
        self,
        decision_engine=None,
        recommendation_engine=None,
    ) -> None:

        self.decision_engine = decision_engine

        self.recommendation_engine = (
            recommendation_engine
        )

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

        result: dict[str, Any] = {

            "investigation_id": investigation.get(
                "id"
            ),

        }


        # AI Decision Layer
        if self.decision_engine:

            decision_result = (
                self.decision_engine.analyze(
                    investigation
                )
            )


            # Normalize decision contract
            if (
                isinstance(
                    decision_result,
                    dict,
                )
                and "decision" in decision_result
                and isinstance(
                    decision_result["decision"],
                    dict,
                )
            ):

                decision_result = (
                    decision_result["decision"]
                )


            result["decision"] = (
                decision_result
            )


        # Recommendation Layer
        if self.recommendation_engine:

            result["recommendations"] = (
                self.recommendation_engine.generate(
                    investigation
                )
            )


        # Store execution history
        self.history.append(
            {
                "investigation": investigation,
                "result": result,
            }
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return integration execution history.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:
        """
        Clear integration execution history.
        """

        self.history.clear()