"""
Sentinel DNA Evidence Intelligence Models.

Defines structured contracts for investigation evidence.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceArtifact:
    """
    Represents a normalized investigation artifact.
    """

    artifact_type: str

    value: Any

    source: str = "unknown"

    risk: str = "low"

    confidence: int = 50

    indicators: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):
        return {
            "artifact_type": self.artifact_type,
            "value": self.value,
            "source": self.source,
            "risk": self.risk,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceCollection:
    """
    Container for investigation evidence artifacts.
    """

    case_id: str

    artifacts: list[EvidenceArtifact] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "case_id": self.case_id,
            "artifacts": [
                artifact.to_dict()
                if hasattr(
                    artifact,
                    "to_dict",
                )
                else artifact
                for artifact in self.artifacts
            ],
            "metadata": self.metadata,
        }