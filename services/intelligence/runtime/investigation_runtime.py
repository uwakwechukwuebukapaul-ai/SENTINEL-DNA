"""
Sentinel DNA - Investigation Runtime

Central execution layer.

Pipeline:

Evidence
    |
Reasoning
    |
Recommendations
    |
Orchestration
    |
Runtime Result

The runtime acts as the integration boundary between
the reasoning/recommendation layers and the investigation
execution orchestrator.

Important:
- Evidence is passed to the orchestrator through `artifacts`.
- The runtime does not introduce an independent `alert` argument.
- Individual subsystem outputs are normalized into RuntimeResult.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.reasoning.reasoning_engine import (
    InvestigationReasoner,
)

from services.intelligence.recommendation.recommendation_engine import (
    RecommendationEngine,
)

from services.intelligence.orchestration import (
    InvestigationOrchestrator,
)

from .runtime_context import RuntimeContext
from .runtime_result import RuntimeResult


class InvestigationRuntime:
    """
    Autonomous investigation runtime.

    Coordinates:
        1. Investigation reasoning
        2. Recommendation generation
        3. Investigation orchestration
        4. Unified runtime result generation
    """

    def __init__(
        self,
        reasoner=None,
        recommendation_engine=None,
        orchestrator=None,
    ) -> None:
        self.reasoner = (
            reasoner
            or InvestigationReasoner()
        )

        self.recommendation_engine = (
            recommendation_engine
            or RecommendationEngine()
        )

        self.orchestrator = (
            orchestrator
            or InvestigationOrchestrator()
        )

    def execute(
        self,
        case_id: str,
        evidence: list[dict[str, Any]] | None = None,
    ) -> RuntimeResult:
        """
        Execute the complete investigation runtime.

        The runtime preserves the established subsystem contracts:

            reasoner.reason(context)
            recommendation_engine.generate(context)
            orchestrator.investigate(
                case_id=case_id,
                artifacts=evidence,
            )

        Returns:
            RuntimeResult
        """

        context = RuntimeContext(
            case_id=case_id,
            evidence=evidence or [],
        )

        try:
            context.update_status("running")

            # ==========================================
            # 1. Investigation reasoning
            # ==========================================

            reasoning = self.reasoner.reason(
                context.to_dict()
            )

            reasoning_result = (
                reasoning.to_dict()
                if hasattr(reasoning, "to_dict")
                else reasoning
            )

            if not isinstance(reasoning_result, dict):
                reasoning_result = {
                    "result": reasoning_result
                }

            # ==========================================
            # 2. Recommendations
            # ==========================================

            recommendations = (
                self.recommendation_engine.generate(
                    context.to_dict()
                )
            )

            if isinstance(
                recommendations,
                dict,
            ):
                recommendation_items = (
                    recommendations.get(
                        "recommendations",
                        [],
                    )
                )
            else:
                recommendation_items = recommendations

            if recommendation_items is None:
                recommendation_items = []

            if not isinstance(
                recommendation_items,
                list,
            ):
                recommendation_items = [
                    recommendation_items
                ]

            # ==========================================
            # 3. Investigation orchestration
            # ==========================================

            # IMPORTANT:
            # The canonical orchestrator contract accepts
            # case_id + artifacts.
            #
            # Do not pass an `alert` keyword here.
            orchestration = (
                self.orchestrator.investigate(
                    case_id=case_id,
                    artifacts=context.evidence,
                )
            )

            if hasattr(
                orchestration,
                "to_dict",
            ):
                orchestration = (
                    orchestration.to_dict()
                )

            if not isinstance(
                orchestration,
                dict,
            ):
                raise TypeError(
                    "Investigation orchestrator "
                    "returned an invalid result type"
                )

            # ==========================================
            # 4. Normalize execution/report
            # ==========================================

            execution = orchestration.get(
                "execution",
                {},
            )

            report = orchestration.get(
                "report",
                {},
            )

            if execution is None:
                execution = {}

            if report is None:
                report = {}

            if not isinstance(
                execution,
                dict,
            ):
                execution = {
                    "result": execution
                }

            if not isinstance(
                report,
                dict,
            ):
                report = {
                    "result": report
                }

            # ==========================================
            # 5. Build unified runtime result
            # ==========================================

            context.update_status(
                "completed"
            )

            return RuntimeResult(
                case_id=case_id,
                status="completed",
                investigation={
                    "analysis": reasoning_result,
                },
                recommendations=(
                    recommendation_items
                ),
                execution=execution,
                report=report,
            )

        except Exception as exc:
            context.update_status(
                "failed"
            )

            return RuntimeResult(
                case_id=case_id,
                status="failed",
                errors=[
                    str(exc)
                ],
            )