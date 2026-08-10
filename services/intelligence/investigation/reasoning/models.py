"""
Reasoning intelligence models.
"""

from dataclasses import dataclass, field


@dataclass
class ReasoningResult:
    """
    AI investigation reasoning output.
    """

    conclusion: str

    risk: str

    confidence: int

    reasoning: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )


    def to_dict(self):

        return {
            "conclusion": self.conclusion,
            "risk": self.risk,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
        }


    def __getitem__(
        self,
        key,
    ):

        return self.to_dict()[key]