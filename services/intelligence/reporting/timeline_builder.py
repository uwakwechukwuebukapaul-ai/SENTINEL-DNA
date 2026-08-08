"""
Sentinel DNA Timeline Builder

Creates investigation timeline events.
"""

from __future__ import annotations

from typing import Any


class TimelineBuilder:
    """
    Builds investigation timelines.
    """

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []

    def build(
        self,
        investigation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build timeline from investigation data.
        """

        case_id = investigation.get(
            "case_id"
        )

        timeline = [
            {
                "case_id": case_id,
                "event": "Investigation created",
                "status": investigation.get(
                    "status",
                    "unknown",
                ),
            }
        ]

        self.history.append(
            {
                "case_id": case_id,
                "timeline": timeline,
            }
        )

        return timeline

    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        return self.history

    def clear_history(
        self,
    ) -> None:
        self.history.clear()