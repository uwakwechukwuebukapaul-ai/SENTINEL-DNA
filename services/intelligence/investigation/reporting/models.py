"""
Sentinel DNA Investigation Report Models.

Defines the normalized report contract consumed by
analyst workspaces, APIs, exports, and future AI Copilot features.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationReport:
    """
    Analyst-ready investigation report.
    """

    case_id: str

    status: str = "completed"

    title: str = "Investigation Report"

    summary: str = ""

    risk: str = "low"

    confidence: int = 50

    findings: list[dict[str, Any]] = field(
        default_factory=list
    )

    mitre_techniques: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the report into an API-safe dictionary.
        """

        return {
            "case_id": self.case_id,
            "status": self.status,
            "title": self.title,
            "summary": self.summary,
            "risk": self.risk,
            "confidence": self.confidence,
            "findings": self.findings,
            "mitre_techniques": self.mitre_techniques,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key: str,
    ):
        """
        Preserve dictionary-style compatibility.
        """

        return self.to_dict()[key]