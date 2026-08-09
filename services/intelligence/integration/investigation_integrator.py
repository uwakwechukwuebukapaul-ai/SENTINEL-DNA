"""
Sentinel DNA Investigation Integrator.

Enterprise workflow coordinator connecting:

- Investigation input
- Decision intelligence
- Recommendation intelligence
- Execution history

"""

from __future__ import annotations

from typing import Any

from services.intelligence.decision.decision_engine import (
    DecisionEngine,
)

from services.intelligence.decision.recommendation_engine import (
    RecommendationEngine,
)


class InvestigationIntegrator:
    """
    Coordinates investigation intelligence execution.
    """

    def __init__(
        self,
        decision_engine=None,
        recommendation_engine=None,
    ) -> None:

        self.decision_engine = (
            decision_engine
            or DecisionEngine()
        )

        self.recommendation_engine = (
            recommendation_engine
            or RecommendationEngine()
        )

        self._history: list[dict[str, Any]] = []


    def process(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute complete investigation workflow.
        """

        normalized = self._normalize_investigation(
            investigation
        )


        decision = self._execute_decision(
            normalized
        )


        recommendations = self._execute_recommendations(
            decision,
            normalized,
        )


        result = {

            "status":
                "completed",

            "investigation_id":
                normalized.get(
                    "id"
                ),

            "decision":
                decision,

            "recommendations":
                recommendations,

        }


        self._history.append(
            result
        )


        return result



    def _execute_decision(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute decision engine safely.
        """

        if hasattr(
            self.decision_engine,
            "analyze",
        ):

            return self.decision_engine.analyze(
                investigation
            )


        if hasattr(
            self.decision_engine,
            "decide",
        ):

            decision = self.decision_engine.decide(
                investigation
            )


            return {

                **decision,

                "decision":
                    self._map_decision(
                        decision
                    ),
            }


        return {

            "status":
                "completed",

            "decision":
                "monitor",

        }



    def _execute_recommendations(
        self,
        decision: dict[str, Any],
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate recommendations.

        Passes full investigation context so
        severity/classification are preserved.
        """

        recommendation_input = {

            **investigation,

            **decision,

        }


        if hasattr(
            self.recommendation_engine,
            "recommend",
        ):

            return self.recommendation_engine.recommend(
                recommendation_input
            )


        if hasattr(
            self.recommendation_engine,
            "generate",
        ):

            return self.recommendation_engine.generate(
                recommendation_input
            )


        return {

            "status":
                "completed",

            "recommendations":
            [
                "Continue monitoring"
            ],

        }



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return execution history.
        """

        return self._history.copy()



    def clear_history(
        self,
    ) -> None:
        """
        Clear execution history.
        """

        self._history.clear()



    def _normalize_investigation(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize incoming investigation.
        """

        return {

            "id":
                investigation.get(
                    "id",
                    "UNKNOWN",
                ),

            "severity":
                investigation.get(
                    "severity",
                    "low",
                ),

            "classification":
                investigation.get(
                    "classification",
                    "unknown",
                ),

            "confidence":
                investigation.get(
                    "confidence",
                    0.0,
                ),

        }



    def _map_decision(
        self,
        result: dict[str, Any],
    ) -> str:
        """
        Convert priority into action.
        """

        priority = result.get(
            "priority",
            "P4",
        )


        if priority in (
            "P1",
            "P2",
        ):
            return "respond"


        return "monitor"