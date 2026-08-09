"""
Fusion Result Models

Defines the unified intelligence output format.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FusionResult:
    """
    Unified threat intelligence result.
    """

    indicator: str

    indicator_type: str | None = None

    risk: str = "unknown"

    confidence: float = 0.0

    providers: list[str] = field(
        default_factory=list
    )

    mitre: list[str] = field(
        default_factory=list
    )

    entities: list[str] = field(
        default_factory=list
    )

    relationships: list[Any] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:
        """
        Serialize result.
        """

        return {
            "indicator": self.indicator,
            "indicator_type": self.indicator_type,
            "risk": self.risk,
            "confidence": self.confidence,
            "providers": self.providers,
            "mitre": self.mitre,
            "entities": self.entities,
            "relationships": self.relationships,
            "metadata": self.metadata,
        }


    def __getitem__(self, key: str):
        """
        Backward compatible dictionary access.
        """

        return self.to_dict().get(key)