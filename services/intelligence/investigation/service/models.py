"""
Unified Investigation Service Models.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationServiceResult:
    """
    Complete AI SOC investigation output.
    """

    case_id: str

    investigation: dict[str, Any] = field(
        default_factory=dict
    )

    decision: dict[str, Any] = field(
        default_factory=dict
    )

    copilot: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "case_id": self.case_id,
            "investigation": self.investigation,
            "decision": self.decision,
            "copilot": self.copilot,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key,
    ):

        return self.to_dict()[key]