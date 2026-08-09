"""
Sentinel DNA Decision Intelligence Engine

Transforms investigation intelligence into
SOC analyst decisions.
"""

from datetime import datetime, timezone
from typing import Any

from .risk_decision import calculate_risk
from .response_planner import ResponsePlanner


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