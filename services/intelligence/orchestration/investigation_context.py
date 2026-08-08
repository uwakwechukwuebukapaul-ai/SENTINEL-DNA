"""
Sentinel DNA Investigation Context

Shared state passed through investigation execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationContext:
    """
    Runtime investigation state.

    Stores all shared investigation data during
    autonomous execution.
    """

    investigation_id: str | None = None

    case_id: str | None = None

    alert: dict[str, Any] | None = None

    alerts: list[dict[str, Any]] = field(
        default_factory=list
    )

    evidence: list[Any] = field(
        default_factory=list
    )

    iocs: list[Any] = field(
        default_factory=list
    )

    timeline: list[Any] = field(
        default_factory=list
    )

    results: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    # --------------------------------------------------
    # Evidence Management
    # --------------------------------------------------

    def add_evidence(
        self,
        item: Any,
    ) -> None:

        self.evidence.append(
            item
        )


    # --------------------------------------------------
    # IOC Management
    # --------------------------------------------------

    def add_ioc(
        self,
        item: Any,
    ) -> None:

        self.iocs.append(
            item
        )


    # --------------------------------------------------
    # Result Management
    # --------------------------------------------------

    def add_result(
        self,
        name: str,
        result: Any,
    ) -> None:
        """
        Store agent execution result.
        """

        if not name:
            raise ValueError(
                "Result name is required"
            )

        self.results[name] = result


    # --------------------------------------------------
    # Timeline Management
    # --------------------------------------------------

    def add_timeline_event(
        self,
        event: Any,
    ) -> None:

        self.timeline.append(
            event
        )


    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "investigation_id": self.investigation_id,
            "case_id": self.case_id,
            "alerts": self.alerts,
            "evidence": self.evidence,
            "iocs": self.iocs,
            "timeline": self.timeline,
            "results": self.results,
            "metadata": self.metadata,
        }