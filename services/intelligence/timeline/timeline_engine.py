"""
Sentinel DNA Timeline Engine

Provides investigation history generation.

TimelineBuilder owns event construction.
TimelineEngine owns execution and serialization.
"""

from __future__ import annotations

from typing import Any

from .timeline_builder import (
    TimelineBuilder,
    TimelineEvent,
)


class TimelineEngine:
    """
    Enterprise timeline processor.
    """


    def __init__(
        self,
    ) -> None:

        self.builder = TimelineBuilder()


    # =================================================
    # GENERATION
    # =================================================

    def generate(
        self,
        events: Any,
    ) -> list[dict[str, Any]]:
        """
        Generate a serialized timeline.

        TimelineBuilder returns TimelineEvent objects.
        The engine exposes dictionaries to API/report layers.
        """

        timeline = self.builder.build(
            events
        )


        return [
            self._serialize_event(
                event
            )
            for event in timeline
        ]


    # =================================================
    # BUILD ALIAS
    # =================================================

    def build(
        self,
        events: Any,
    ) -> list[dict[str, Any]]:
        """
        Compatibility alias for generate().
        """

        return self.generate(
            events
        )


    # =================================================
    # SERIALIZATION
    # =================================================

    @staticmethod
    def _serialize_event(
        event: Any,
    ) -> dict[str, Any]:
        """
        Convert TimelineEvent or compatible objects
        into dictionaries.
        """

        if isinstance(
            event,
            TimelineEvent,
        ):

            return event.to_dict()


        if isinstance(
            event,
            dict,
        ):

            return dict(
                event
            )


        if hasattr(
            event,
            "to_dict",
        ):

            try:

                result = event.to_dict()

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
            event,
            "__dict__",
        ):

            return {
                key: value
                for key, value
                in vars(event).items()
                if not key.startswith("_")
            }


        return {
            "event_type": "unknown",
            "description": str(event),
            "source": "unknown",
            "severity": "unknown",
            "timestamp": "",
        }


__all__ = [
    "TimelineEngine",
]