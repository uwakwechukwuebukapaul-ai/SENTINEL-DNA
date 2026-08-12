from dataclasses import dataclass, field
from typing import Any


@dataclass
class FusionEvidence:
    """
    Normalized evidence contribution used during fusion.
    """

    source: str

    category: str

    value: Any

    confidence: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class FusionResult:
    """
    Final intelligence fusion output.

    Combines evidence sources into
    one investigation intelligence object.
    """

    confidence: float

    verdict: str

    contributing_sources: list[str] = field(
        default_factory=list
    )

    evidence_count: int = 0

    signals: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "verdict": self.verdict,
            "contributing_sources": (
                self.contributing_sources
            ),
            "evidence_count": self.evidence_count,
            "signals": self.signals,
            "metadata": self.metadata,
        }