"""
Correlation Result Model

Unified result object supporting:
- attribute access
- dictionary style access
- serialization
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorrelationResult:

    matched: bool

    risk: str

    confidence: float = 0.0

    entities: list[str] = field(
        default_factory=list
    )

    relationships: list[Any] = field(
        default_factory=list
    )

    attack_pattern: str | None = None

    mitre: list[str] = field(
        default_factory=list
    )

    entity_type: str | None = None

    value: str | None = None

    metadata: dict = field(
        default_factory=dict
    )


    def __post_init__(self):

        if not self.metadata:

            self.metadata = {}


        if "mitre" not in self.metadata:

            self.metadata["mitre"] = self.mitre


        if not self.mitre:

            self.mitre = (
                self.metadata.get(
                    "mitre",
                    []
                )
            )


    def __getitem__(
        self,
        key: str,
    ):

        return getattr(
            self,
            key,
            self.metadata.get(key),
        )


    def to_dict(self):

        return {

            "matched": self.matched,

            "risk": self.risk,

            "confidence": self.confidence,

            "entities": self.entities,

            "relationships": self.relationships,

            "attack_pattern": self.attack_pattern,

            "mitre": self.mitre,

            "entity_type": self.entity_type,

            "value": self.value,

            "metadata": self.metadata,

        }