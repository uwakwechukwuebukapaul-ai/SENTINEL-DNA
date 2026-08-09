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
        Core AI decision evaluation.
        """

        severity = (
            alert.get(
                "severity",
                "unknown",
            )
            .lower()
        )


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


        decision = (
            self._select_decision(
                severity
            )
        )


        result = {

            "decision": decision,

            "risk": risk,

            "priority": priority,

            "strategy": strategy,

            "actions": actions,

        }


        self.history.append(
            {
                "alert": alert,
                "decision": result,
            }
        )


        return result



    def _select_decision(
        self,
        severity: str,
    ) -> str:
        """
        Map severity into response action.
        """

        if severity in {
            "critical",
            "high",
        }:
            return "respond_immediately"


        if severity == "medium":
            return "investigate_further"


        return "monitor"



    def decide(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Backward compatible decision API.
        """

        result = self.evaluate(
            alert
        )


        return result



    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Integration compatibility API.
        """

        result = self.evaluate(
            investigation
        )


        # Integration layer expects:
        # result["decision"]["decision"]

        return {
            "decision": {
                "decision": (
                    "respond"
                    if investigation.get(
                        "severity",
                        "",
                    ).lower()
                    in {
                        "critical",
                        "high",
                    }
                    else "investigate"
                )
            },

            "analysis": result,
        }



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