"""
Sentinel DNA Investigation Service Models.

Shared contracts for unified investigation services.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationServiceResult:
    """
    Unified investigation service response contract.
    """

    case_id: str

    status: str = "completed"

    investigation: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "investigation": self.investigation,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key,
    ):
        return self.to_dict()[key]