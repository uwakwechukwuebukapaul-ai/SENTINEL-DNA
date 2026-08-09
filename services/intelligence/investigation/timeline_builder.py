"""
Sentinel DNA Investigation Timeline Builder
"""

from __future__ import annotations

from datetime import datetime, timezone

from typing import Any


class TimelineBuilder:


    def build(
        self,
        result,
    ) -> list[dict[str, Any]]:


        timeline = []


        timeline.append(
            {
                "event":
                    "investigation_started",

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            }
        )


        for ioc in result.iocs:

            timeline.append(
                {
                    "event":
                        "ioc_detected",

                    "value":
                        ioc.get(
                            "value"
                        ),

                    "timestamp":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                }
            )


        return timeline