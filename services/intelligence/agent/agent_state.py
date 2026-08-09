"""
Agent State Management.

Tracks investigation execution state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any



@dataclass
class AgentState:
    """
    Represents current investigation state.
    """

    case_id: str

    status: str = "initialized"

    current_step: str = ""

    findings: list[dict[str, Any]] = field(
        default_factory=list
    )

    timeline: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )



    def update_status(
        self,
        status: str,
    ) -> None:
        """
        Update execution status.
        """

        self.status = status



    def add_finding(
        self,
        finding: dict[str, Any],
    ) -> None:
        """
        Store investigation finding.
        """

        self.findings.append(
            finding
        )



    def add_timeline_event(
        self,
        event: dict[str, Any],
    ) -> None:
        """
        Add timeline event.
        """

        event = dict(event)

        event.setdefault(
            "timestamp",
            datetime.now(
                timezone.utc
            ).isoformat(),
        )

        self.timeline.append(
            event
        )



    def export(
        self,
    ) -> dict[str, Any]:
        """
        Serialize state.
        """

        return {
            "case_id": self.case_id,
            "status": self.status,
            "current_step": self.current_step,
            "findings": self.findings,
            "timeline": self.timeline,
            "metadata": self.metadata,
        }