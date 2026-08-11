"""
Sentinel DNA Investigation Execution Orchestrator

Coordinates investigation execution across intelligence engines.

Responsibilities:

- Execute investigation pipeline
- Normalize intelligence outputs
- Produce canonical InvestigationResult
- Maintain execution history
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

    Flow:

    Investigation Pipeline
            |
            v
    Intelligence Results
            |
            v
    InvestigationResult
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
        """
        Execute investigation workflow.
        """

        pipeline_result = self.pipeline.execute(
            case_id,
            alert,
        )


        findings = getattr(
            pipeline_result,
            "findings",
            [],
        )


        correlation = getattr(
            pipeline_result,
            "correlation",
            None,
        )


        fusion = getattr(
            pipeline_result,
            "fusion",
            None,
        )


        reasoning = getattr(
            pipeline_result,
            "reasoning",
            None,
        )


        recommendations = getattr(
            pipeline_result,
            "recommendations",
            [],
        )


        intelligence = getattr(
            pipeline_result,
            "intelligence",
            {},
        )


        result = InvestigationResult(
            success=True,
            status="completed",
            message="Investigation completed successfully.",

            case_id=case_id,

            findings=findings,

            correlation=(
                correlation
                if correlation is not None
                else {
                    "status": "completed",
                    "matches": [],
                }
            ),

            fusion=(
                fusion
                if fusion is not None
                else {
                    "status": "completed",
                    "signals": [],
                }
            ),

            reasoning=(
                reasoning
                if reasoning is not None
                else {
                    "status": "completed",
                    "analysis": [],
                }
            ),

            recommendations=recommendations,

            intelligence=(
                intelligence
                if intelligence
                else {
                    "status": "completed",
                }
            ),

            execution={
                "pipeline": pipeline_result,
            },
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