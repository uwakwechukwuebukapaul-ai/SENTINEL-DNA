"""
Sentinel DNA Investigation Context.

Shared state container passed through
the investigation lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationContext:
    """
    Enterprise investigation state.

    Maintains a single source of truth
    during investigation execution.
    """

    case_id: str

    investigation_id: str | None = None

    artifacts: list[dict[str, Any]] = field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = field(
        default_factory=list
    )

    intelligence: dict[str, Any] = field(
        default_factory=dict
    )

    decisions: list[dict[str, Any]] = field(
        default_factory=list
    )

    actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    timeline: list[dict[str, Any]] = field(
        default_factory=list
    )

    report: dict[str, Any] = field(
        default_factory=dict
    )


    status: str = "created"


    def add_event(
        self,
        event: dict[str, Any],
    ) -> None:
        """
        Add investigation timeline event.
        """

        self.timeline.append(
            event
        )


    def add_evidence(
        self,
        evidence: dict[str, Any],
    ) -> None:

        self.evidence.append(
            evidence
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


    def set_intelligence(
        self,
        intelligence: dict[str, Any],
    ) -> None:

        self.intelligence = intelligence


    def set_report(
        self,
        report: dict[str, Any],
    ) -> None:

        self.report = report


    def complete(self) -> None:

        self.status = "completed"


    def fail(
        self,
    ) -> None:

        self.status = "failed"


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {

            "case_id":
                self.case_id,

            "investigation_id":
                self.investigation_id,

            "status":
                self.status,

            "artifacts":
                self.artifacts,

            "evidence":
                self.evidence,

            "intelligence":
                self.intelligence,

            "decisions":
                self.decisions,

            "actions":
                self.actions,

            "timeline":
                self.timeline,

            "report":
                self.report,

        }