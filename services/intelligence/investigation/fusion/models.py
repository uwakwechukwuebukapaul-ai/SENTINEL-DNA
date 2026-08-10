"""
Sentinel DNA Investigation Fusion Models.

Unified intelligence objects for SOC investigations.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationIntelligence:
    """
    Final fused investigation intelligence result.
    """

    case_id: str

    risk: str

    confidence: int

    threat_summary: str

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


    def to_dict(self):

        return {
            "case_id": self.case_id,
            "risk": self.risk,
            "confidence": self.confidence,
            "threat_summary": self.threat_summary,
            "findings": self.findings,
            "mitre_techniques": self.mitre_techniques,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key,
    ):

        return self.to_dict()[key]