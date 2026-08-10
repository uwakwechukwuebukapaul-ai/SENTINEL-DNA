"""
Sentinel DNA Investigation Timeline Intelligence Engine.

Builds a normalized, chronological investigation timeline from
evidence, IOC intelligence, threat intelligence, and runtime events.

Design goals:
- deterministic
- analyst-readable
- backwards compatible
- security-first
- dependency-light
- suitable for future event-stream expansion
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InvestigationTimelineEngine:
    """
    Builds a unified investigation timeline.

    The engine accepts heterogeneous event dictionaries and produces
    a stable InvestigationTimeline-compatible representation.
    """

    def build(
        self,
        case_id: str,
        events: Any = None,
        evidence: Any = None,
        iocs: Any = None,
        threats: Any = None,
    ):
        """
        Build a normalized investigation timeline.

        Parameters
        ----------
        case_id:
            Investigation case identifier.

        events:
            Optional explicit timeline events.

        evidence:
            Optional evidence records.

        iocs:
            Optional IOC records.

        threats:
            Optional threat intelligence records.

        Returns
        -------
        InvestigationTimeline
            Normalized timeline model.
        """

        normalized_events: list[Any] = []

        # ---------------------------------------------------------
        # 1. Explicit runtime events
        # ---------------------------------------------------------

        for event in self._normalize_collection(events):
            normalized_events.append(
                self._normalize_event(
                    event,
                    source="runtime",
                )
            )

        # ---------------------------------------------------------
        # 2. Evidence events
        # ---------------------------------------------------------

        for item in self._normalize_collection(evidence):
            normalized_events.append(
                self._normalize_event(
                    item,
                    source="evidence",
                    default_event_type="evidence_observed",
                )
            )

        # ---------------------------------------------------------
        # 3. IOC events
        # ---------------------------------------------------------

        for item in self._normalize_collection(iocs):
            normalized_events.append(
                self._normalize_event(
                    item,
                    source="ioc_intelligence",
                    default_event_type="ioc_identified",
                )
            )

        # ---------------------------------------------------------
        # 4. Threat intelligence events
        # ---------------------------------------------------------

        for item in self._normalize_collection(threats):
            normalized_events.append(
                self._normalize_event(
                    item,
                    source="threat_intelligence",
                    default_event_type="threat_identified",
                )
            )

        # ---------------------------------------------------------
        # 5. Stable chronological ordering
        # ---------------------------------------------------------

        normalized_events.sort(
            key=self._event_sort_key
        )

        # ---------------------------------------------------------
        # 6. Calculate timeline risk
        # ---------------------------------------------------------

        risk = self._calculate_risk(
            normalized_events
        )

        first_event = (
            normalized_events[0]
            if normalized_events
            else None
        )

        last_event = (
            normalized_events[-1]
            if normalized_events
            else None
        )

        metadata = {
            "engine": "investigation_timeline_intelligence",
            "event_count": len(
                normalized_events
            ),
            "risk": risk,
            "first_event": (
                self._event_timestamp(
                    first_event
                )
                if first_event
                else None
            ),
            "last_event": (
                self._event_timestamp(
                    last_event
                )
                if last_event
                else None
            ),
        }

        return self._create_timeline(
            case_id=case_id,
            events=normalized_events,
            risk=risk,
            metadata=metadata,
        )

    # =============================================================
    # Normalization
    # =============================================================

    def _normalize_collection(
        self,
        value: Any,
    ) -> list[Any]:
        """
        Normalize arbitrary input into a list.
        """

        if value is None:
            return []

        if isinstance(value, list):
            return list(value)

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, set):
            return list(value)

        return [value]

    def _normalize_event(
        self,
        event: Any,
        source: str,
        default_event_type: str = "investigation_event",
    ) -> dict[str, Any]:
        """
        Convert an arbitrary event object into a stable dictionary.
        """

        if event is None:
            data: dict[str, Any] = {}

        elif isinstance(event, dict):
            data = dict(event)

        else:
            to_dict = getattr(
                event,
                "to_dict",
                None,
            )

            if callable(to_dict):
                converted = to_dict()

                if isinstance(
                    converted,
                    dict,
                ):
                    data = dict(converted)

                else:
                    data = {
                        "value": converted,
                    }

            else:
                data = {
                    "value": str(event),
                }

        timestamp = self._extract_timestamp(
            data
        )

        event_type = (
            data.get("event_type")
            or data.get("type")
            or data.get("category")
            or default_event_type
        )

        value = (
            data.get("value")
            or data.get("indicator")
            or data.get("name")
            or data.get("description")
            or event_type
        )

        risk = self._normalize_risk(
            data.get(
                "risk",
                data.get(
                    "severity",
                    "low",
                ),
            )
        )

        normalized = {
            "timestamp": timestamp,
            "event_type": str(
                event_type
            ),
            "source": str(
                data.get(
                    "source",
                    source,
                )
            ),
            "value": str(
                value
            ),
            "risk": risk,
            "attributes": data,
        }

        return normalized

    # =============================================================
    # Timestamp handling
    # =============================================================

    def _extract_timestamp(
        self,
        data: dict[str, Any],
    ) -> str:
        """
        Extract and normalize an event timestamp.

        Supported fields:
        - timestamp
        - time
        - event_time
        - occurred_at
        - created_at
        """

        candidates = (
            "timestamp",
            "time",
            "event_time",
            "occurred_at",
            "created_at",
        )

        for field in candidates:
            value = data.get(field)

            if value is None:
                continue

            if isinstance(
                value,
                datetime,
            ):
                return self._normalize_datetime(
                    value
                )

            text = str(
                value
            ).strip()

            if text:
                parsed = self._parse_datetime(
                    text
                )

                if parsed is not None:
                    return self._normalize_datetime(
                        parsed
                    )

                return text

        return self._current_timestamp()

    def _parse_datetime(
        self,
        value: str,
    ) -> datetime | None:
        """
        Parse common ISO-8601 timestamps.
        """

        text = value.strip()

        if text.endswith("Z"):
            text = (
                text[:-1]
                + "+00:00"
            )

        try:
            return datetime.fromisoformat(
                text
            )

        except ValueError:
            return None

    def _normalize_datetime(
        self,
        value: datetime,
    ) -> str:
        """
        Normalize datetime values to UTC ISO-8601.
        """

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        value = value.astimezone(
            timezone.utc
        )

        return value.isoformat()

    def _current_timestamp(
        self,
    ) -> str:
        """
        Generate a UTC timestamp.

        Kept isolated so deterministic testing can monkeypatch
        this method if necessary.
        """

        return datetime.now(
            timezone.utc
        ).isoformat()

    def _event_sort_key(
        self,
        event: dict[str, Any],
    ):
        """
        Produce a stable chronological sorting key.
        """

        timestamp = event.get(
            "timestamp",
            "",
        )

        parsed = self._parse_datetime(
            str(timestamp)
        )

        if parsed is None:
            return (
                datetime.max.replace(
                    tzinfo=timezone.utc
                ),
                str(timestamp),
            )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return (
            parsed.astimezone(
                timezone.utc
            ),
            str(timestamp),
        )

    def _event_timestamp(
        self,
        event: dict[str, Any],
    ) -> str | None:
        """
        Safely extract an event timestamp.
        """

        if not event:
            return None

        value = event.get(
            "timestamp"
        )

        if value is None:
            return None

        return str(value)

    # =============================================================
    # Risk
    # =============================================================

    def _normalize_risk(
        self,
        risk: Any,
    ) -> str:
        """
        Normalize risk/severity labels.
        """

        value = str(
            risk or "low"
        ).strip().lower()

        aliases = {
            "informational": "low",
            "info": "low",
            "warning": "medium",
            "moderate": "medium",
            "severe": "high",
            "urgent": "critical",
        }

        value = aliases.get(
            value,
            value,
        )

        if value in {
            "critical",
            "high",
            "medium",
            "low",
            "unknown",
        }:
            return value

        return "unknown"

    def _calculate_risk(
        self,
        events: list[dict[str, Any]],
    ) -> str:
        """
        Calculate highest observed timeline risk.
        """

        priority = {
            "unknown": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

        highest = "low"

        for event in events:
            risk = self._normalize_risk(
                event.get(
                    "risk",
                    "low",
                )
            )

            if priority.get(
                risk,
                0,
            ) > priority.get(
                highest,
                0,
            ):
                highest = risk

        return highest

    # =============================================================
    # Model compatibility
    # =============================================================

    def _create_timeline(
        self,
        case_id: str,
        events: list[dict[str, Any]],
        risk: str,
        metadata: dict[str, Any],
    ):
        """
        Construct the project timeline model.

        Supports both the current model contract and compatible
        constructor variants used by earlier Sentinel DNA layers.
        """

        from .models import (
            InvestigationTimeline,
        )

        payload = {
            "case_id": case_id,
            "events": events,
            "risk": risk,
            "metadata": metadata,
        }

        try:
            return InvestigationTimeline(
                **payload
            )

        except TypeError:
            # Compatibility with models that may not expose
            # risk directly.
            payload.pop(
                "risk",
                None,
            )

            try:
                return InvestigationTimeline(
                    **payload
                )

            except TypeError:
                # Final compatibility fallback for models with
                # minimal constructor contracts.
                timeline = InvestigationTimeline(
                    case_id=case_id,
                    events=events,
                )

                if hasattr(
                    timeline,
                    "risk",
                ):
                    timeline.risk = risk

                if hasattr(
                    timeline,
                    "metadata",
                ):
                    timeline.metadata = metadata

                return timeline