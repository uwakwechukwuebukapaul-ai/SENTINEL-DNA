"""
Sentinel DNA Investigation Timeline Intelligence Engine.

Transforms raw investigation events into a normalized,
chronological, analyst-ready investigation timeline.

Responsibilities:

    Raw Events
        ↓
    Normalization
        ↓
    Chronological Ordering
        ↓
    Risk Assessment
        ↓
    Investigation Phase Detection
        ↓
    Timeline Narrative
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import (
    InvestigationTimeline,
    TimelineEvent,
)


class InvestigationTimelineEngine:
    """
    Builds deterministic investigation timelines.

    The engine is intentionally provider-independent.

    External enrichment remains the responsibility of:

        - IOC intelligence
        - Threat intelligence
        - Evidence intelligence
        - Graph intelligence
        - Detection providers

    This engine focuses specifically on temporal
    investigation intelligence.
    """

    RISK_ORDER = {
        "unknown": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    PHASE_KEYWORDS = {
        "initial_access": {
            "phishing",
            "initial access",
            "email",
            "attachment",
            "malicious link",
            "credential harvesting",
            "credential phishing",
        },
        "execution": {
            "execution",
            "command execution",
            "script",
            "powershell",
            "process",
            "payload",
            "malware execution",
        },
        "persistence": {
            "persistence",
            "scheduled task",
            "registry",
            "startup",
            "service",
            "autorun",
        },
        "credential_access": {
            "credential",
            "password",
            "credential harvesting",
            "keylogging",
            "authentication",
            "credential dumping",
        },
        "discovery": {
            "discovery",
            "enumeration",
            "scan",
            "scanning",
            "reconnaissance",
            "system discovery",
            "network discovery",
        },
        "lateral_movement": {
            "lateral",
            "lateral movement",
            "remote",
            "rdp",
            "smb",
            "movement",
            "remote service",
        },
        "collection": {
            "collection",
            "archive",
            "staging",
            "data collection",
            "file collection",
        },
        "command_and_control": {
            "c2",
            "command and control",
            "beacon",
            "callback",
            "remote control",
            "command channel",
        },
        "exfiltration": {
            "exfiltration",
            "exfil",
            "data transfer",
            "upload",
            "data theft",
        },
        "impact": {
            "impact",
            "ransomware",
            "encryption",
            "destruction",
            "denial of service",
            "data destruction",
        },
    }

    def build(
        self,
        case_id: str,
        events: list[Any] | None = None,
    ) -> InvestigationTimeline:
        """
        Build an investigation timeline.

        Parameters
        ----------
        case_id:
            Investigation/case identifier.

        events:
            Raw investigation events.

        Returns
        -------
        InvestigationTimeline
            Normalized and chronologically ordered timeline.
        """

        normalized_events = self._normalize_events(
            events or []
        )

        normalized_events.sort(
            key=self._timestamp_sort_key
        )

        risk = self._calculate_risk(
            normalized_events
        )

        phases = self._detect_phases(
            normalized_events
        )

        narrative = self._build_narrative(
            normalized_events,
            risk,
            phases,
        )

        return InvestigationTimeline(
            case_id=case_id,
            events=normalized_events,
            risk=risk,
            phases=phases,
            narrative=narrative,
            metadata={
                "engine": (
                    "investigation_timeline_intelligence"
                ),
                "event_count": len(
                    normalized_events
                ),
                "phase_count": len(
                    phases
                ),
                "high_risk_event_count": sum(
                    1
                    for event in normalized_events
                    if event.risk
                    in {
                        "high",
                        "critical",
                    }
                ),
                "critical_event_count": sum(
                    1
                    for event in normalized_events
                    if event.risk == "critical"
                ),
            },
        )

    def _normalize_events(
        self,
        events: list[Any],
    ) -> list[TimelineEvent]:
        """
        Normalize arbitrary event input.
        """

        result: list[TimelineEvent] = []

        for index, event in enumerate(events):
            if isinstance(
                event,
                TimelineEvent,
            ):
                result.append(
                    event
                )
                continue

            if hasattr(
                event,
                "to_dict",
            ):
                event = event.to_dict()

            if not isinstance(
                event,
                dict,
            ):
                event = {
                    "description": str(
                        event
                    )
                }

            result.append(
                self._normalize_event(
                    event,
                    index,
                )
            )

        return result

    def _normalize_event(
        self,
        event: dict[str, Any],
        index: int,
    ) -> TimelineEvent:
        """
        Convert one raw event into a TimelineEvent.
        """

        timestamp = str(
            event.get(
                "timestamp",
                event.get(
                    "time",
                    event.get(
                        "created_at",
                        "",
                    ),
                ),
            )
            or ""
        )

        event_type = str(
            event.get(
                "event_type",
                event.get(
                    "type",
                    "observation",
                ),
            )
            or "observation"
        )

        source = str(
            event.get(
                "source",
                "unknown",
            )
            or "unknown"
        )

        description = str(
            event.get(
                "description",
                event.get(
                    "message",
                    event.get(
                        "value",
                        event_type,
                    ),
                ),
            )
            or event_type
        )

        severity = self._normalize_risk(
            event.get(
                "severity",
                event.get(
                    "risk",
                    "low",
                ),
            )
        )

        risk = self._normalize_risk(
            event.get(
                "risk",
                event.get(
                    "severity",
                    "low",
                ),
            )
        )

        entity = event.get(
            "entity"
        )

        indicator = event.get(
            "indicator"
        )

        mitre_techniques = self._normalize_strings(
            event.get(
                "mitre_techniques",
                event.get(
                    "attack_patterns",
                    [],
                ),
            )
        )

        event_id = str(
            event.get(
                "event_id",
                f"event-{index + 1}",
            )
        )

        return TimelineEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            source=source,
            description=description,
            severity=severity,
            risk=risk,
            entity=(
                str(entity)
                if entity is not None
                else None
            ),
            indicator=(
                str(indicator)
                if indicator is not None
                else None
            ),
            mitre_techniques=mitre_techniques,
            attributes=dict(
                event
            ),
        )

    def _normalize_risk(
        self,
        value: Any,
    ) -> str:
        """
        Normalize risk/severity labels.
        """

        normalized = str(
            value or "low"
        ).strip().lower()

        if normalized in {
            "critical",
            "high",
            "medium",
            "low",
            "unknown",
        }:
            return normalized

        if normalized in {
            "severe",
            "urgent",
            "emergency",
        }:
            return "critical"

        if normalized in {
            "moderate",
            "warning",
            "warn",
        }:
            return "medium"

        if normalized in {
            "dangerous",
            "elevated",
        }:
            return "high"

        if normalized in {
            "informational",
            "info",
            "notice",
        }:
            return "low"

        return "unknown"

    def _normalize_strings(
        self,
        values: Any,
    ) -> list[str]:
        """
        Normalize values into unique strings
        while preserving insertion order.
        """

        if values is None:
            return []

        if not isinstance(
            values,
            (
                list,
                tuple,
                set,
            ),
        ):
            values = [
                values
            ]

        result: list[str] = []

        for value in values:
            text = str(
                value
            ).strip()

            if (
                text
                and text not in result
            ):
                result.append(
                    text
                )

        return result

    def _timestamp_sort_key(
        self,
        event: TimelineEvent,
    ):
        """
        Produce a stable chronological sort key.

        Valid timestamps are ordered first.

        Missing or invalid timestamps are placed after
        valid timestamps while maintaining deterministic
        event ordering.
        """

        if not event.timestamp:
            return (
                1,
                datetime.max,
                event.event_id,
            )

        value = event.timestamp.strip()

        try:
            normalized = value.replace(
                "Z",
                "+00:00",
            )

            parsed = datetime.fromisoformat(
                normalized
            )

            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(
                    tzinfo=None
                )

            return (
                0,
                parsed,
                event.event_id,
            )

        except (
            ValueError,
            TypeError,
        ):
            return (
                1,
                datetime.max,
                event.event_id,
            )

    def _calculate_risk(
        self,
        events: list[TimelineEvent],
    ) -> str:
        """
        Calculate overall timeline risk.

        The highest observed event risk becomes the
        timeline risk.
        """

        if not events:
            return "low"

        highest_score = max(
            (
                self.RISK_ORDER.get(
                    event.risk,
                    0,
                )
                for event in events
            ),
            default=1,
        )

        for risk, score in (
            self.RISK_ORDER.items()
        ):
            if score == highest_score:
                return risk

        return "unknown"

    def _detect_phases(
        self,
        events: list[TimelineEvent],
    ) -> list[str]:
        """
        Infer investigation phases from event content.

        Phase ordering follows chronological discovery
        rather than dictionary ordering.
        """

        phases: list[str] = []

        for event in events:
            searchable = " ".join(
                [
                    event.event_type,
                    event.description,
                    event.source,
                    event.indicator or "",
                    " ".join(
                        event.mitre_techniques
                    ),
                ]
            ).lower()

            for phase, keywords in (
                self.PHASE_KEYWORDS.items()
            ):
                if any(
                    keyword in searchable
                    for keyword in keywords
                ):
                    if phase not in phases:
                        phases.append(
                            phase
                        )

        return phases

    def _build_narrative(
        self,
        events: list[TimelineEvent],
        risk: str,
        phases: list[str],
    ) -> str:
        """
        Build deterministic analyst-readable narrative.
        """

        if not events:
            return (
                "No investigation events were available "
                "to construct a timeline."
            )

        event_count = len(
            events
        )

        phase_text = (
            ", ".join(
                phases
            )
            if phases
            else "no distinct attack phases"
        )

        high_risk_count = sum(
            1
            for event in events
            if event.risk
            in {
                "high",
                "critical",
            }
        )

        if risk in {
            "critical",
            "high",
        }:
            opening = (
                "The investigation timeline contains "
                f"{event_count} event(s) and reaches "
                f"{risk} risk."
            )
        else:
            opening = (
                "The investigation timeline contains "
                f"{event_count} event(s) with an overall "
                f"{risk} risk assessment."
            )

        risk_statement = (
            f" {high_risk_count} high-severity event(s) "
            "require analyst attention."
            if high_risk_count
            else ""
        )

        return (
            f"{opening}"
            f"{risk_statement} "
            "Observed investigation phases: "
            f"{phase_text}."
        )