from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """
    Represents a knowledge graph entity.
    """

    id: str
    entity_type: str
    value: str
    metadata: dict[str, Any] = field(default_factory=dict)


    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "value": self.value,
            "metadata": self.metadata,
        }