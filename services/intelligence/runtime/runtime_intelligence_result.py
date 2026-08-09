"""
Runtime Intelligence Result

Standard output contract for intelligence execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeIntelligenceResult:

    success: bool

    risk: str = "unknown"

    confidence: float = 0.0

    mitre: list[str] = field(
        default_factory=list
    )

    entities: list[Any] = field(
        default_factory=list
    )

    providers: list[str] = field(
        default_factory=list
    )

    correlations: list[Any] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "success": self.success,
            "risk": self.risk,
            "confidence": self.confidence,
            "mitre": self.mitre,
            "entities": self.entities,
            "providers": self.providers,
            "correlations": self.correlations,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }