"""
Sentinel DNA Investigation Execution Orchestrator

Coordinates investigation execution across intelligence engines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .investigation_pipeline import InvestigationPipeline
from .intelligence_factory import IntelligenceFactory
from .investigation_result import InvestigationResult


class InvestigationExecutionOrchestrator:
    """
    Enterprise investigation execution coordinator.
    """

    def __init__(
        self,
        pipeline: InvestigationPipeline | None = None,
    ) -> None:

        self.pipeline = (
            pipeline
            if pipeline is not None
            else IntelligenceFactory.create_pipeline()
        )

        self.history: list[dict[str, Any]] = []


    def execute_investigation(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:

        pipeline_result = self.pipeline.execute(
            case_id,
            alert,
        )


        findings = getattr(
            pipeline_result,
            "findings",
            {},
        )


        result = InvestigationResult(
            case_id=case_id,
            status="completed",
            findings=findings,
        )


        self.history.append(
            {
                "case_id": case_id,
                "status": result.status,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )


        return result


    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history


    def get_execution_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history


    def clear_history(
        self,
    ) -> None:

        self.history.clear()


    def clear_execution_history(
        self,
    ) -> None:

        self.history.clear()