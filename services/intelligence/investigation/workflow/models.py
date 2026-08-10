"""
Sentinel DNA Investigation Workflow Models.

Contracts for investigation lifecycle execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationWorkflowResult:
    """
    Final workflow execution result.
    """

    case_id: str

    status: str = "completed"

    result: dict[str, Any] = field(
        default_factory=dict
    )

    stages: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(self) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "status": self.status,
            "result": self.result,
            "stages": self.stages,
            "metadata": self.metadata,
        }


    def __getitem__(
        self,
        key,
    ):

        return self.to_dict()[key]