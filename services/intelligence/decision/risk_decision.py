"""
Risk Decision Engine

Evaluates investigation confidence,
severity, and indicators to produce
a risk decision.
"""

from dataclasses import dataclass


@dataclass
class RiskDecision:
    """
    Represents SOC risk judgement.
    """

    severity: str
    confidence: float
    priority: str
    rationale: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "confidence": self.confidence,
            "priority": self.priority,
            "rationale": self.rationale,
        }


def calculate_risk(
    indicators: list,
    confidence: float,
) -> RiskDecision:
    """
    Calculate investigation risk.
    """

    indicator_count = len(indicators)

    if indicator_count >= 3 and confidence >= 0.8:
        return RiskDecision(
            severity="critical",
            confidence=confidence,
            priority="immediate",
            rationale=(
                "Multiple indicators with "
                "high confidence detected."
            ),
        )

    if indicator_count > 0:
        return RiskDecision(
            severity="high",
            confidence=confidence,
            priority="urgent",
            rationale=(
                "Suspicious activity requires "
                "analyst investigation."
            ),
        )

    return RiskDecision(
        severity="low",
        confidence=confidence,
        priority="monitor",
        rationale=(
            "No significant malicious indicators found."
        ),
    )