"""
Correlation Result

Data contract representing intelligence
correlation output between IOC matching,
threat analysis, and investigation workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorrelationResult:
    """
    Intelligence correlation result object.

    Used by:
    - Correlation Engine
    - Investigation Intelligence
    - Analyst APIs
    - Reporting pipelines
    """

    case_id: str = ""

    matched: bool = False

    risk: str = "unknown"

    confidence: float = 0.0

    indicators: list[dict[str, Any]] = field(
        default_factory=list
    )

    matched_iocs: list[Any] = field(
        default_factory=list
    )

    entities: list[str] = field(
        default_factory=list
    )

    techniques: list[Any] = field(
        default_factory=list
    )

    correlations: Any = field(
        default_factory=list
    )

    attack_story: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = ""


    def __post_init__(self):
        """
        Normalize correlation state.
        """

        if self.matched_iocs:
            self.matched = True


        if self.correlations:
            if isinstance(
                self.correlations,
                dict
            ):
                self.risk = (
                    self.correlations.get(
                        "risk",
                        self.risk,
                    )
                )


        if not self.metadata:
            self.metadata = {
                "engine": "sentinel-dna-correlation",
                "version": "1.0",
            }


    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize result for APIs.
        """

        return {
            "case_id": self.case_id,

            "matched": self.matched,

            "risk": self.risk,

            "confidence": self.confidence,

            "indicators": self.indicators,

            "matched_iocs": self.matched_iocs,

            "entities": self.entities,

            "techniques": self.techniques,

            "correlations": self.correlations,

            "attack_story": self.attack_story,

            "metadata": self.metadata,

            "created_at": self.created_at,
        }