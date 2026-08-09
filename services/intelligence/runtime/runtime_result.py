"""
Sentinel DNA - Runtime Result

Unified output object from
investigation execution.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeResult:
    """
    Investigation runtime response.
    """

    case_id: str

    status: str

    investigation: dict[str, Any] = field(
        default_factory=dict
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    execution: dict[str, Any] = field(
        default_factory=dict
    )

    report: dict[str, Any] = field(
        default_factory=dict
    )

    errors: list[str] = field(
        default_factory=list
    )


    def to_dict(self) -> dict[str, Any]:
        """
        Convert runtime result to API format.
        """

        return {

            "case_id":
                self.case_id,

            "status":
                self.status,

            "investigation":
                self.investigation,

            "recommendations":
                self.recommendations,

            "execution":
                self.execution,

            "report":
                self.report,

            "errors":
                self.errors,

        }


    def __getitem__(
        self,
        key: str,
    ):

        return self.to_dict()[key]