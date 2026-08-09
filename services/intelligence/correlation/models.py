from dataclasses import dataclass


@dataclass
class CorrelationResult:

    matched: bool

    risk: str

    entity_type: str | None = None

    value: str | None = None

    confidence: float = 0.0

    entities: list[str] | None = None

    relationships: list | None = None


    def to_dict(self):

        return {
            "matched": self.matched,
            "risk": self.risk,
            "entity_type": self.entity_type,
            "value": self.value,
            "confidence": self.confidence,
            "entities": self.entities or [],
            "relationships": self.relationships or [],
        }