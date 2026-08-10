"""
Sentinel DNA Investigation Memory.

Maintains investigation knowledge
during autonomous investigation lifecycle.
"""

from __future__ import annotations

from typing import Any


class InvestigationMemory:
    """
    Investigation intelligence memory store.

    Stores:
    - findings
    - indicators
    - decisions
    - actions
    - confidence history
    """


    def __init__(
        self,
        investigation_id: str,
    ) -> None:

        self.investigation_id = investigation_id

        self.findings: list[dict[str, Any]] = []

        self.indicators: list[dict[str, Any]] = []

        self.decisions: list[dict[str, Any]] = []

        self.actions: list[dict[str, Any]] = []

        self.confidence_history: list[float] = []



    def add_finding(
        self,
        finding: dict[str, Any],
    ) -> None:

        self.findings.append(
            finding
        )



    def add_indicator(
        self,
        indicator: dict[str, Any],
    ) -> None:

        self.indicators.append(
            indicator
        )



    def add_decision(
        self,
        decision: dict[str, Any],
    ) -> None:

        self.decisions.append(
            decision
        )



    def add_action(
        self,
        action: dict[str, Any],
    ) -> None:

        self.actions.append(
            action
        )



    def add_confidence(
        self,
        confidence: float,
    ) -> None:

        self.confidence_history.append(
            confidence
        )



    def snapshot(self) -> dict[str, Any]:
        """
        Return intelligence memory snapshot.
        """

        return {

            "investigation_id":
                self.investigation_id,


            "findings":
                self.findings,


            "indicators":
                self.indicators,


            "decisions":
                self.decisions,


            "actions":
                self.actions,


            "confidence_history":
                self.confidence_history,

        }