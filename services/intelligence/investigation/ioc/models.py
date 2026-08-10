"""
Sentinel DNA IOC Intelligence Models.

Defines structured contracts for
indicator intelligence.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IOCRecord:
    """
    Represents a single enriched indicator.
    """

    indicator: str

    indicator_type: str = "unknown"

    risk: str = "low"

    confidence: int = 50

    reputation: str = "unknown"

    mitre_techniques: list[str] = field(
        default_factory=list
    )

    sources: list[str] = field(
        default_factory=list
    )

    context: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "indicator": self.indicator,
            "indicator_type": self.indicator_type,
            "risk": self.risk,
            "confidence": self.confidence,
            "reputation": self.reputation,
            "mitre_techniques": self.mitre_techniques,
            "sources": self.sources,
            "context": self.context,
        }



@dataclass
class IOCCollection:
    """
    Collection of enriched indicators.
    """

    case_id: str

    indicators: list[IOCRecord] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "indicators": [

                indicator.to_dict()

                for indicator
                in self.indicators

            ],

            "metadata":
                self.metadata,
        }