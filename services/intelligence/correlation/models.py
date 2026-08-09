"""
Correlation data models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any



@dataclass
class CorrelationResult:
    """
    Output of intelligence correlation.
    """

    case_id: str

    indicators: list[dict[str, Any]] = field(
        default_factory=list
    )

    techniques: list[dict[str, Any]] = field(
        default_factory=list
    )

    attack_story: list[str] = field(
        default_factory=list
    )

    confidence: float = 0.0


    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "case_id": self.case_id,
            "indicators": self.indicators,
            "techniques": self.techniques,
            "attack_story": self.attack_story,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }