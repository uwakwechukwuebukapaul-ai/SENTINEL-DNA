from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    source: str
    timestamp: str
    severity: str
    entities: list[dict[str, Any]] = field(default_factory=list)
    raw_event: dict[str, Any] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        return {"event_id": self.event_id, "source": self.source, "timestamp": self.timestamp, "severity": self.severity, "entities": self.entities, "raw_event": self.raw_event}

def event_id(value: Any) -> str:
    return str(value) if value else str(uuid4())
