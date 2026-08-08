"""
Sentinel DNA Investigation Result

Standard output object for AI investigations.
"""

from __future__ import annotations

from typing import Any


class InvestigationResult:
    """
    Represents completed investigation output.
    """

    def __init__(
        self,
        case_id: str,
        status: str = "completed",
    ) -> None:

        self.case_id = case_id
        self.status = status

        self.findings: dict[str, Any] = {}

        self.timeline: list[dict[str, Any]] = []

        self.recommendations: list[str] = []


    def add_finding(
        self,
        name: str,
        result: Any,
    ) -> None:

        self.findings[name] = result


    def add_timeline_event(
        self,
        event: dict[str, Any],
    ) -> None:

        self.timeline.append(event)


    def add_recommendation(
        self,
        recommendation: str,
    ) -> None:

        self.recommendations.append(
            recommendation
        )


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "status": self.status,
            "findings": self.findings,
            "timeline": self.timeline,
            "recommendations": self.recommendations,
        }