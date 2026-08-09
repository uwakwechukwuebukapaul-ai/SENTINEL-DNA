"""
Sentinel DNA - Runtime Context

Maintains investigation execution state.

Responsible for carrying:

- case information
- evidence
- metadata
- execution lifecycle data
"""


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RuntimeContext:
    """
    Investigation execution context.
    """

    case_id: str

    evidence: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda:
            datetime.now(
                timezone.utc
            ).isoformat()
    )

    status: str = "created"


    def update_status(
        self,
        status: str,
    ):
        """
        Update runtime lifecycle state.
        """

        self.status = status


    def add_metadata(
        self,
        key: str,
        value: Any,
    ):
        """
        Add execution metadata.
        """

        self.metadata[key] = value


    def to_dict(self) -> dict[str, Any]:
        """
        Serialize context.
        """

        return {
            "case_id": self.case_id,
            "evidence": self.evidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "status": self.status,
        }