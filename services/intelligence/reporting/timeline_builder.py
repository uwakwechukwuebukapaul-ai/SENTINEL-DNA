"""
Sentinel DNA Timeline Builder
"""

from __future__ import annotations

from datetime import datetime, timezone

from typing import Any


class TimelineBuilder:
    """
    Creates investigation timeline events.
    """

    def build(
        self,
        investigation: dict[str, Any],
    ) -> list[dict[str, Any]]:

        timeline = []

        timeline.append(
            {
                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "event":
                    "investigation_completed",

                "case_id":
                    investigation.get(
                        "case_id"
                    ),
            }
        )

        return timeline