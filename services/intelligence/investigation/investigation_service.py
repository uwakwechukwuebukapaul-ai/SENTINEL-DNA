"""
Sentinel DNA Investigation Service

Application service layer for investigations.
"""

from __future__ import annotations

from typing import Any

from .execution_orchestrator import (
    InvestigationExecutionOrchestrator,
)

from .investigation_result import (
    InvestigationResult,
)



class InvestigationService:
    """
    High-level investigation service.

    Provides a stable interface between
    platform components and investigation engines.
    """

    def __init__(
        self,
        orchestrator: InvestigationExecutionOrchestrator | None = None,
    ) -> None:

        self.orchestrator = (
            orchestrator
            or InvestigationExecutionOrchestrator()
        )


    def investigate(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:
        """
        Start an investigation.
        """

        return (
            self.orchestrator.execute_investigation(
                case_id=case_id,
                alert=alert,
            )
        )


    def get_investigation_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return previous executions.
        """

        return (
            self.orchestrator.get_history()
        )


    def clear_history(
        self,
    ) -> None:
        """
        Clear investigation execution history.
        """

        self.orchestrator.clear_history()