from dataclasses import asdict, dataclass, field
from typing import Any


class TelemetryValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SecurityAlert:
    alert_id: str
    source: str
    timestamp: str
    title: str
    severity: str
    description: str
    entities: dict[str, list[str]] = field(default_factory=dict)
    raw_event: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_investigation_alert(self) -> dict[str, Any]:
        entity_text = []
        for entity_type, values in self.entities.items():
            if values:
                entity_text.append(f"{entity_type}: {', '.join(values)}")
        body = self.description
        if entity_text:
            body = f"{body}\nEntities: {'; '.join(entity_text)}" if body else f"Entities: {'; '.join(entity_text)}"
        return {
            "alert_id": self.alert_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "title": self.title,
            "subject": self.title,
            "severity": self.severity,
            "description": self.description,
            "body": body,
            "entities": self.entities,
            "metadata": self.metadata,
            "raw_event": self.raw_event,
        }
