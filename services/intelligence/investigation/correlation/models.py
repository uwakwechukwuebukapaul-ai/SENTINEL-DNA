"""
Correlation intelligence models.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CorrelationFinding:
    """
    Represents an intelligence finding.
    """

    category: str
    value: str
    risk: str
    confidence: int

    metadata: dict = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "category": self.category,
            "value": self.value,
            "risk": self.risk,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class IntelligenceResult:
    """
    Result of evidence correlation.
    """

    findings: List[CorrelationFinding] = field(
        default_factory=list
    )


    def add(
        self,
        finding: CorrelationFinding,
    ):

        self.findings.append(
            finding
        )


    def to_dict(self):

        return {
            "findings": [
                item.to_dict()
                for item in self.findings
            ]
        }