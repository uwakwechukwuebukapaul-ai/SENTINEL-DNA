"""
Sentinel DNA Case Timeline

Tracks investigation events.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any


class CaseTimeline:
    """
    Investigation event timeline.
    """

    def __init__(self) -> None:

        self.events: list[dict[str, Any]] = []


    def add_event(
        self,
        event_type: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Add investigation event.
        """

        event = {
            "timestamp": datetime.now(
                UTC
            ).isoformat(),

            "type": event_type,

            "description": description,

            "metadata": metadata or {},
        }

        self.events.append(event)

        return event


    def get_events(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return investigation timeline events.
        """

        return self.events