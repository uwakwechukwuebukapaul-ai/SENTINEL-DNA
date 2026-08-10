"""
Sentinel DNA Investigation Timeline Models.

Stable contracts for chronological investigation intelligence.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimelineEvent:
    """
    Represents one normalized investigation event.
    """

    event_id: str
    timestamp: str
    event_type: str
    source: str
    description: str
    severity: str = "low"
    risk: str = "low"
    entity: str | None = None
    indicator: str | None = None
    mitre_techniques: list[str] = field(
        default_factory=list
    )
    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source,
            "description": self.description,
            "severity": self.severity,
            "risk": self.risk,
            "entity": self.entity,
            "indicator": self.indicator,
            "mitre_techniques": list(
                self.mitre_techniques
            ),
            "attributes": dict(
                self.attributes
            ),
        }

    def __getitem__(self, key):
        return self.to_dict()[key]


@dataclass
class InvestigationTimeline:
    """
    Chronological investigation timeline.
    """

    case_id: str
    events: list[TimelineEvent] = field(
        default_factory=list
    )
    risk: str = "low"
    phases: list[str] = field(
        default_factory=list
    )
    narrative: str = ""
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "events": [
                event.to_dict()
                if hasattr(event, "to_dict")
                else event
                for event in self.events
            ],
            "risk": self.risk,
            "phases": list(
                self.phases
            ),
            "narrative": self.narrative,
            "metadata": dict(
                self.metadata
            ),
        }

    def __getitem__(self, key):
        return self.to_dict()[key]