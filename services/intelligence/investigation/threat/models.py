"""
Sentinel DNA Threat Intelligence Models.

Defines stable contracts for correlated threat intelligence.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ThreatContext:
    """
    Represents correlated intelligence for an indicator
    or investigation artifact.
    """

    indicator: str

    threat_name: str = "Unknown Threat"

    actor: str = "Unknown"

    campaign: str = "Unknown"

    severity: str = "low"

    confidence: int = 50

    mitre_techniques: list[str] = field(
        default_factory=list
    )

    attack_patterns: list[str] = field(
        default_factory=list
    )

    related_indicators: list[str] = field(
        default_factory=list
    )

    sources: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the threat context into a serializable
        dictionary.
        """

        return {
            "indicator": self.indicator,
            "threat_name": self.threat_name,
            "actor": self.actor,
            "campaign": self.campaign,
            "severity": self.severity,
            "confidence": self.confidence,
            "mitre_techniques": list(
                self.mitre_techniques
            ),
            "attack_patterns": list(
                self.attack_patterns
            ),
            "related_indicators": list(
                self.related_indicators
            ),
            "sources": list(
                self.sources
            ),
            "metadata": dict(
                self.metadata
            ),
        }

    def __getitem__(self, key: str) -> Any:
        """
        Provide dictionary-style compatibility.
        """

        return self.to_dict()[key]


@dataclass
class ThreatIntelligenceCollection:
    """
    Collection of correlated threat intelligence.
    """

    case_id: str

    threats: list[ThreatContext] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the collection into a serializable
        dictionary.
        """

        return {
            "case_id": self.case_id,
            "threats": [
                threat.to_dict()
                if hasattr(
                    threat,
                    "to_dict",
                )
                else threat
                for threat in self.threats
            ],
            "metadata": dict(
                self.metadata
            ),
        }

    def __getitem__(self, key: str) -> Any:
        """
        Provide dictionary-style compatibility.
        """

        return self.to_dict()[key]