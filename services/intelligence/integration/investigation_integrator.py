"""
Sentinel DNA Investigation Integrator

Connects intelligence engines into a unified
investigation execution workflow.
"""

from __future__ import annotations

from typing import Any


class InvestigationIntegrator:
    """
    Coordinates investigation intelligence flow.

    Pipeline:

    Investigation
          |
          ↓
    Decision Engine
          |
          ↓
    Recommendation Engine
          |
          ↓
    Reporting Layer
    """


    def __init__(
        self,
        decision_engine=None,
        recommendation_engine=None,
        report_engine=None,
    ) -> None:

        self.decision_engine = (
            decision_engine
        )

        self.recommendation_engine = (
            recommendation_engine
        )

        self.report_engine = (
            report_engine
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

            result["decision"] = (
                self.decision_engine.analyze(
                    investigation
                )
            )


        # Recommendation Layer
        if self.recommendation_engine:

            result["recommendations"] = (
                self.recommendation_engine.generate(
                    investigation
                )
            )


        # Reporting Layer
        if self.report_engine:

            result["report"] = (
                self.report_engine.generate(
                    investigation,
                    result,
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
        """
        Clear execution history.
        """

        self.history.clear()