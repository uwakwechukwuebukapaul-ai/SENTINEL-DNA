"""
Sentinel DNA Runtime Models.

Execution contracts for investigation runtime.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeResult:

    case_id: str

    status: str = "completed"

    report: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self):

        return {
            "case_id": self.case_id,
            "status": self.status,
            "report": self.report,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key,
    ):

        return self.to_dict()[key]