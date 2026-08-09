"""
Runtime Investigation Context

Shared state container for autonomous investigations.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeInvestigationContext:
    """
    Investigation execution state.
    """

    investigation_id: str

    signals: list[dict[str, Any]] = field(
        default_factory=list
    )

    intelligence_result: Any = None

    decisions: list[Any] = field(
        default_factory=list
    )

    timeline: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def add_event(
        self,
        event: dict[str, Any],
    ):
        self.timeline.append(event)


    def add_decision(
        self,
        decision: Any,
    ):
        self.decisions.append(decision)