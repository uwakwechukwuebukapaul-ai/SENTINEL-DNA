"""
Sentinel DNA Investigation API Models.

Defines request and response contracts
for investigation interfaces.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationRequest:
    """
    Incoming investigation request.
    """

    case_id: str

    evidence: Any

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }



@dataclass
class InvestigationResponse:
    """
    API investigation response contract.
    """

    case_id: str

    status: str = "completed"

    result: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "status": self.status,
            "result": self.result,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key,
    ):

        return self.to_dict()[key]