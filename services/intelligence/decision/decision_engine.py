"""
Sentinel DNA Autonomous Decision Engine

Central intelligence layer responsible for
investigation reasoning and strategy selection.
"""

from __future__ import annotations

from typing import Any

from .risk_classifier import RiskClassifier
from .priority_engine import PriorityEngine
from .investigation_strategy import InvestigationStrategy
from .threat_reasoner import ThreatReasoner


class DecisionEngine:
    """
    AI decision intelligence coordinator.
    """

    def __init__(
        self,
        risk_classifier=None,
        priority_engine=None,
        strategy=None,
        reasoner=None,
    ) -> None:

        self.risk_classifier = (
            risk_classifier
            or RiskClassifier()
        )

        self.priority_engine = (
            priority_engine
            or PriorityEngine()
        )

        self.strategy = (
            strategy
            or InvestigationStrategy()
        )

        self.reasoner = (
            reasoner
            or ThreatReasoner()
        )

        self.history: list[
            dict[str, Any]
        ] = []


    def evaluate(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Core decision intelligence method.
        """

        risk = (
            self.risk_classifier
            .classify(alert)
        )


        priority = (
            self.priority_engine
            .calculate(risk)
        )


        strategy = (
            self.strategy
            .select(alert)
        )


        actions = (
            self.reasoner
            .analyze(alert)
        )


        decision_action = (
            self._determine_decision(
                alert,
                risk,
            )
        )


        decision = {

            "decision": decision_action,

            "risk": risk,

            "priority": priority,

            "strategy": strategy,

            "actions": actions,

        }


        self.history.append(
            {
                "alert": alert,
                "decision": decision,
            }
        )


        return decision



    def _determine_decision(
        self,
        alert: dict[str, Any],
        risk: Any,
    ) -> str:
        """
        Determine analyst action.

        Compatibility layer for
        existing Sentinel DNA workflows.
        """

        severity = (
            str(
                alert.get(
                    "severity",
                    "",
                )
            )
            .lower()
        )


        if severity == "critical":

            return "respond"


        if severity == "high":

            return "respond_immediately"


        if severity == "medium":

            return "investigate_further"


        if str(risk).lower() == "high":

            return "respond_immediately"


        return "monitor"



    def decide(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Backward compatible decision API.
        """

        return self.evaluate(
            alert
        )



    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Integration compatibility API.
        """

        return self.evaluate(
            investigation
        )



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