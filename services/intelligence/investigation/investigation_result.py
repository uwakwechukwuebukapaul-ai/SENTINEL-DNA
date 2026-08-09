"""
Sentinel DNA Investigation Result

Standard investigation execution output object.
"""

from __future__ import annotations

from typing import Any


class InvestigationResult:
    """
    Represents completed investigation output.

    Supports:
    - findings
    - metadata
    - timeline events
    - analyst enrichment
    """

    def __init__(
        self,
        case_id: str,
        status: str,
        findings: dict[str, Any] | None = None,
    ) -> None:

        self.case_id = case_id

        self.status = status

        self.findings = (
            findings
            if findings is not None
            else {}
        )

        self.metadata: dict[str, Any] = {}

        self.timeline: list[dict[str, Any]] = []



    def update_metadata(
        self,
        metadata: dict[str, Any],
    ) -> None:
        """
        Attach investigation metadata.

        Used by:
        - investigation context
        - AI reasoning layer
        - reporting layer
        """

        self.metadata.update(
            metadata
        )



    def add_timeline_event(
        self,
        event: dict[str, Any],
    ) -> None:

        self.timeline.append(
            event
        )



    def get_metadata(
        self,
    ) -> dict[str, Any]:

        return self.metadata



    def get_timeline(
        self,
    ) -> list[dict[str, Any]]:

        return self.timeline



    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "case_id": self.case_id,

            "status": self.status,

            "findings": self.findings,

            "metadata": self.metadata,

            "timeline": self.timeline,
        }