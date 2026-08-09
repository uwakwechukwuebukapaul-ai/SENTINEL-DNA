"""
Sentinel DNA - Event Gateway

Enterprise entry point for security
event ingestion.
"""

from __future__ import annotations

from typing import Any


from .event_normalizer import (
    EventNormalizer,
)



class EventGateway:
    """
    Receives external security events
    and prepares them for investigation.
    """



    def __init__(
        self,
        normalizer: EventNormalizer | None = None,
        adapter=None,
    ):

        self.normalizer = (
            normalizer
            or EventNormalizer()
        )

        self.adapter = adapter



    def ingest(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process incoming security event.
        """


        normalized = (
            self.normalizer.normalize(
                event
            )
        )


        if self.adapter:

            return self.adapter.process_alert(

                {

                    "case_id":
                        normalized["case_id"],

                    "source":
                        normalized["source"],

                    "severity":
                        normalized["severity"],

                    "indicator":
                        (
                            normalized["indicators"][0]
                            if normalized["indicators"]
                            else None
                        ),

                }

            )


        return normalized