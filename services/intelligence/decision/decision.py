"""
Sentinel DNA Decision Intelligence Engine

Transforms investigation intelligence into
SOC analyst decisions.
"""

from datetime import datetime, timezone
from importlib import import_module
from typing import Any

try:
    calculate_risk = import_module(
        ".risk_decision",
        package=__package__,
    ).calculate_risk
except (ImportError, AttributeError):
    def calculate_risk(
        indicators: Any,
        confidence: Any,
    ) -> Any:
        """Raise a clear error when the risk calculator is unavailable."""
        raise ImportError(
            "The risk decision module is unavailable."
        )


try:
    ResponsePlanner = import_module(
        ".response_planner",
        package=__package__,
    ).ResponsePlanner
except (ImportError, AttributeError):
    class ResponsePlanner:
        """Fallback planner used when the optional planner module is absent."""

        def generate(self, risk: Any) -> list[Any]:
            return []


class DecisionEngine:
    """
    Decision orchestration layer.

    Responsibilities:
    - Evaluate investigation risk
    - Generate response recommendations
    - Maintain decision history
    - Provide explainable decisions
    """

    def __init__(
        self,
        response_planner=None,
    ):

        self.response_planner = (
            response_planner
            or ResponsePlanner()
        )

        self.history: list[dict[str, Any]] = []


    def decide(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate SOC decision.
        """


        if investigation is None:
            investigation = {}


        indicators = investigation.get(
            "indicators",
            [],
        )


        confidence = investigation.get(
            "confidence",
            0.0,
        )


        case_id = investigation.get(
            "case_id",
            "UNKNOWN",
        )


        risk = calculate_risk(
            indicators,
            confidence,
        )


        actions = (
            self.response_planner.generate(
                risk
            )
        )


        decision = {

            "case_id":
                case_id,


            "risk":
                risk.to_dict(),


            "recommended_actions":
                actions,


            "explanation":
                risk.rationale,


            "confidence":
                confidence,


            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }


        self.history.append(
            decision
        )


        return decision



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return decision history.
        """

        return self.history.copy()



    def clear_history(
        self,
    ) -> None:
        """
        Clear decision history.
        """

        self.history.clear()