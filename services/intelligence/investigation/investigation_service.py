"""
Sentinel DNA Investigation Service

High level investigation API.
"""

from __future__ import annotations

from typing import Any

from .execution_orchestrator import (
    InvestigationExecutionOrchestrator,
)

from .investigation_result import (
    InvestigationResult,
)

from .intelligence_factory import (
    IntelligenceFactory,
)


class InvestigationService:
    """
    Application investigation service.
    """

    def __init__(
        self,
        orchestrator:
        InvestigationExecutionOrchestrator
        | None = None,
    ) -> None:

        pipeline = (
            IntelligenceFactory
            .create_pipeline()
        )

        self.orchestrator = (
            orchestrator
            or InvestigationExecutionOrchestrator(
                pipeline=pipeline
            )
        )


    def investigate(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:

        return (
            self.orchestrator
            .execute_investigation(
                case_id=case_id,
                alert=alert,
            )
        )


    def get_investigation_history(
        self,
    ):

        return (
            self.orchestrator
            .get_history()
        )


    def clear_history(
        self,
    ):

        self.orchestrator.clear_history()