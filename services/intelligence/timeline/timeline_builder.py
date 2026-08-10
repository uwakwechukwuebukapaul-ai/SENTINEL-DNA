"""
Sentinel DNA Timeline Builder

Creates normalized investigation timeline events.

The builder returns TimelineEvent objects while preserving
dictionary-style compatibility for downstream consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class TimelineEvent:
    """
    Canonical Sentinel DNA timeline event.

    Supports both:

        event.event_type

    and:

        event["event_type"]
    """

    event_type: str = "unknown"

    description: str = "Unknown event"

    source: str = "unknown"

    severity: str = "unknown"

    timestamp: str = ""


    def __getitem__(
        self,
        key: str,
    ) -> Any:
        """
        Dictionary-style access.
        """

        return self.to_dict()[key]


    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Dictionary-style get().
        """

        return self.to_dict().get(
            key,
            default,
        )


    def keys(self):
        """
        Dictionary compatibility.
        """

        return self.to_dict().keys()


    def values(self):
        """
        Dictionary compatibility.
        """

        return self.to_dict().values()


    def items(self):
        """
        Dictionary compatibility.
        """

        return self.to_dict().items()


    def __contains__(
        self,
        key: str,
    ) -> bool:
        """
        Dictionary compatibility.
        """

        return key in self.to_dict()


    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize the timeline event.
        """

        return {
            "event_type":
                self.event_type,

            "description":
                self.description,

            "source":
                self.source,

            "severity":
                self.severity,

            "timestamp":
                self.timestamp,
        }


class TimelineBuilder:
    """
    Enterprise investigation timeline builder.
    """


    def build(
        self,
        events: Any,
    ) -> list[TimelineEvent]:
        """
        Build normalized timeline events.

        Supported inputs:

        - list of dictionaries
        - single dictionary
        - TimelineEvent
        - arbitrary objects with to_dict()
        - strings
        - timeline envelopes containing "events"
        """

        if events is None:
            return []


        # ---------------------------------------------
        # Existing TimelineEvent
        # ---------------------------------------------

        if isinstance(
            events,
            TimelineEvent,
        ):

            return [
                events
            ]


        # ---------------------------------------------
        # Timeline envelope
        # ---------------------------------------------

        if isinstance(
            events,
            dict,
        ):

            if "events" in events:

                events = events.get(
                    "events",
                    [],
                )

            else:

                events = [
                    events
                ]


        # ---------------------------------------------
        # Single event object
        # ---------------------------------------------

        elif not isinstance(
            events,
            list,
        ):

            events = [
                events
            ]


        timeline: list[
            TimelineEvent
        ] = []


        # ---------------------------------------------
        # Normalize
        # ---------------------------------------------

        for event in events:

            normalized = self._normalize(
                event
            )

            if not normalized:
                continue


            timeline.append(
                self._build_event(
                    normalized
                )
            )


        # ---------------------------------------------
        # Chronological order
        # ---------------------------------------------

        timeline.sort(
            key=lambda item:
                item.timestamp
        )


        return timeline


    # =================================================
    # EVENT CREATION
    # =================================================

    def _build_event(
        self,
        event: dict[str, Any],
    ) -> TimelineEvent:
        """
        Create canonical TimelineEvent.
        """

        event_type = (
            event.get(
                "event_type"
            )
            or event.get(
                "type"
            )
            or event.get(
                "kind"
            )
            or "unknown"
        )


        description = (
            event.get(
                "description"
            )
            or event.get(
                "event"
            )
            or event.get(
                "message"
            )
            or event.get(
                "value"
            )
            or "Unknown event"
        )


        source = (
            event.get(
                "source"
            )
            or event.get(
                "origin"
            )
            or "unknown"
        )


        severity = (
            event.get(
                "severity"
            )
            or event.get(
                "risk"
            )
            or "unknown"
        )


        timestamp = (
            event.get(
                "timestamp"
            )
            or event.get(
                "created_at"
            )
            or event.get(
                "occurred_at"
            )
            or self._timestamp()
        )


        return TimelineEvent(

            event_type=str(
                event_type
            ),

            description=str(
                description
            ),

            source=str(
                source
            ),

            severity=str(
                severity
            ),

            timestamp=str(
                timestamp
            ),

        )


    # =================================================
    # INPUT NORMALIZATION
    # =================================================

    @staticmethod
    def _normalize(
        value: Any,
    ) -> dict[str, Any]:
        """
        Convert arbitrary input into a dictionary.
        """

        if value is None:
            return {}


        if isinstance(
            value,
            TimelineEvent,
        ):

            return value.to_dict()


        if isinstance(
            value,
            dict,
        ):

            return dict(
                value
            )


        if isinstance(
            value,
            str,
        ):

            return {
                "description":
                    value,
            }


        if hasattr(
            value,
            "to_dict",
        ):

            try:

                result = value.to_dict()

                if isinstance(
                    result,
                    dict,
                ):

                    return dict(
                        result
                    )

            except Exception:
                pass


        if hasattr(
            value,
            "__dict__",
        ):

            return {
                key: item
                for key, item
                in vars(value).items()
                if not key.startswith("_")
            }


        return {}


    # =================================================
    # TIMESTAMP
    # =================================================

    @staticmethod
    def _timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()


__all__ = [
    "TimelineEvent",
    "TimelineBuilder",
]