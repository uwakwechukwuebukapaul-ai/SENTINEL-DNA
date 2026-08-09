"""
Sentinel DNA - Investigation Execution State

Tracks investigation workflow lifecycle.
"""


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class WorkflowState:
    """
    Investigation workflow state manager.
    """

    current_status: str = "created"

    history: list[str] = field(default_factory=list)

    updated_at: str = field(
        default_factory=lambda:
        datetime.now(timezone.utc).isoformat()
    )


    def status(self) -> str:
        """
        Compatibility API.
        """

        return self.current_status


    def set_status(
        self,
        status: str,
    ):
        """
        Update workflow state.
        """

        self.current_status = status

        self.history.append(
            status
        )

        self.updated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )


    def transition(
        self,
        status: str,
    ):
        """
        Alias used by future runtime.
        """

        self.set_status(
            status
        )


    def to_dict(self):
        return {
            "status":
                self.current_status,

            "history":
                self.history,

            "updated_at":
                self.updated_at,
        }