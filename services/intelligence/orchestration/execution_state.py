"""
Sentinel DNA Workflow Execution State.

Tracks investigation workflow lifecycle.
"""

from __future__ import annotations


class WorkflowState:
    """
    Investigation workflow state manager.
    """

    def __init__(self) -> None:

        self._status = "created"


    # =====================================================
    # STATUS MANAGEMENT
    # =====================================================

    def set_status(
        self,
        status: str,
    ) -> None:
        """
        Update workflow status.
        """

        self._status = status



    def status(
        self,
    ) -> str:
        """
        Return current workflow status.
        """

        return self._status



    # =====================================================
    # SERIALIZATION
    # =====================================================

    def to_dict(
        self,
    ) -> dict[str, str]:

        return {
            "status": self._status
        }