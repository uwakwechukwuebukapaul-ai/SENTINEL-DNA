"""
Sentinel DNA Decision Intelligence Models.

Defines decision contracts for SOC automation.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DecisionResult:
    """
    Final SOC decision output.
    """

    case_id: str

    decision: str

    priority: str

    rationale: str

    actions: list[str] = field(
        default_factory=list
    )

    confidence: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "case_id": self.case_id,
            "decision": self.decision,
            "priority": self.priority,
            "rationale": self.rationale,
            "actions": self.actions,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }