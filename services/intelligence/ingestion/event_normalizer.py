"""
Sentinel DNA - Event Normalizer

Converts external security events
into Sentinel DNA internal schema.
"""

from __future__ import annotations

from typing import Any



class EventNormalizer:
    """
    Normalizes events from SIEM/XDR
    platforms.
    """



    def normalize(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert external event format
        into Sentinel DNA format.
        """


        source = (
            event.get(
                "source"
            )
            or
            event.get(
                "vendor"
            )
            or
            "unknown"
        )


        case_id = (
            event.get(
                "case_id"
            )
            or
            event.get(
                "id"
            )
            or
            "UNKNOWN"
        )


        severity = (
            event.get(
                "severity"
            )
            or
            event.get(
                "Severity"
            )
            or
            "unknown"
        )


        indicators = []


        if event.get("indicator"):

            indicators.append(
                event["indicator"]
            )


        if event.get("ioc"):

            indicators.append(
                event["ioc"]
            )


        if event.get("ip"):

            indicators.append(
                event["ip"]
            )


        return {

            "case_id":
                case_id,

            "source":
                source,

            "severity":
                str(
                    severity
                ).lower(),

            "indicators":
                indicators,

            "raw_event":
                event,

        }