"""Models for normalized investigation timelines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationTimelineEvent:
    timestamp: str
    event_type: str
    source: str
    description: str
    severity: str = "info"
    related_iocs: list[Any] = field(default_factory=list)
    mitre_techniques: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
