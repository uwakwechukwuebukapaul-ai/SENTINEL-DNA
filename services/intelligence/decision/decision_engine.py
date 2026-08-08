"""
Sentinel DNA AI Decision Engine

Combines intelligence outputs into
a final security decision.
"""

from __future__ import annotations

from typing import Any


class DecisionEngine:
    """
    Generates explainable AI security decisions.
    """

    def __init__(
        self,
        risk_engine=None,
        recommendation_engine=None,
        confidence_engine=None,
    ) -> None:

        self.risk_engine = risk_engine

        self.recommendation_engine = (
            recommendation_engine
        )

        self.confidence_engine = (
            confidence_engine
        )

        self.history: list[
            dict[str, Any]
        ] = []


    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Integration API.

        Used by InvestigationIntegrator.

        Converts internal AI decisions
        into SOC workflow actions.
        """

        result = self.decide(
            investigation
        )

        decision_map = {
            "respond_immediately": "respond",
            "investigate_further": "investigate",
            "monitor": "monitor",
        }

        result["decision"] = decision_map.get(
            result["decision"],
            result["decision"],
        )

        return result


    def decide(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate final AI security decision.
        """

        risk = {}

        if self.risk_engine:

            risk = self.risk_engine.analyze(
                investigation
            )


        recommendations = {}

        if self.recommendation_engine:

            recommendations = (
                self.recommendation_engine.generate(
                    investigation
                )
            )


        confidence = {}

        if self.confidence_engine:

            confidence = (
                self.confidence_engine.calculate(
                    investigation
                )
            )


        decision = {

            "case_id": investigation.get(
                "id"
            ),

            "risk": risk,

            "recommendations": (
                recommendations.get(
                    "recommendations",
                    [],
                )
                if recommendations
                else []
            ),

            "confidence": confidence,

            "decision": self._decision(
                investigation
            ),
        }


        self.history.append(
            decision
        )


        return decision


    def _decision(
        self,
        investigation: dict[str, Any],
    ) -> str:
        """
        Determine AI security decision.

        Internal reasoning states:

        critical/high:
            respond_immediately

        medium:
            investigate_further

        low/unknown:
            monitor
        """

        severity = investigation.get(
            "severity",
            "",
        ).lower()


        if severity in (
            "critical",
            "high",
        ):

            return "respond_immediately"


        if severity == "medium":

            return "investigate_further"


        return "monitor"


    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return decision history.
        """

        return self.history


    def clear_history(
        self,
    ) -> None:
        """
        Clear decision history.
        """

        self.history.clear()