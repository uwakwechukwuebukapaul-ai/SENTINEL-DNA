"""
Sentinel DNA Investigation Execution Orchestrator

Coordinates autonomous investigation execution.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from .investigation_pipeline import (
    InvestigationPipeline,
)

from .investigation_result import (
    InvestigationResult,
)


class InvestigationExecutionOrchestrator:
    """
    Main coordinator for AI investigation execution.

    Responsible for:
    - starting investigations
    - tracking execution lifecycle
    - recording audit history
    """


    def __init__(
        self,
        pipeline: InvestigationPipeline | None = None,
    ) -> None:

        self.pipeline = (
            pipeline
            or InvestigationPipeline()
        )

        self.execution_history: list[
            dict[str, Any]
        ] = []


    def execute_investigation(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:
        """
        Execute complete investigation workflow.
        """

        started = datetime.now(
            UTC
        )

        started_at = started.isoformat()


        try:

            result = self.pipeline.execute(
                case_id=case_id,
                alert=alert,
            )


            completed = datetime.now(
                UTC
            )


            self._record_execution(
                case_id=case_id,
                status=result.status,
                started_at=started_at,
                completed_at=completed.isoformat(),
                duration=(
                    completed - started
                ).total_seconds(),
                result=result.to_dict(),
            )


            return result


        except Exception as exc:

            completed = datetime.now(
                UTC
            )


            self._record_execution(
                case_id=case_id,
                status="failed",
                started_at=started_at,
                completed_at=completed.isoformat(),
                duration=(
                    completed - started
                ).total_seconds(),
                result={
                    "error": str(exc),
                },
            )


            raise



    def _record_execution(
        self,
        case_id: str,
        status: str,
        started_at: str,
        completed_at: str,
        duration: float,
        result: dict[str, Any],
    ) -> None:
        """
        Store execution audit record.
        """

        self.execution_history.append(
            {
                "case_id": case_id,
                "status": status,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_seconds": duration,
                "result": result,
            }
        )



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return investigation execution history.
        """

        return self.execution_history



    def clear_history(
        self,
    ) -> None:
        """
        Clear execution history.
        """

        self.execution_history.clear()