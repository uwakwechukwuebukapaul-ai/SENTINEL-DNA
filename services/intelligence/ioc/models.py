"""
IOC Intelligence Data Models
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IOCResult:
    """
    Result produced by IOC enrichment.
    """

    indicator: str

    indicator_type: str

    risk: str

    confidence: float

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:

        return {
            "indicator": self.indicator,
            "indicator_type": self.indicator_type,
            "risk": self.risk,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }