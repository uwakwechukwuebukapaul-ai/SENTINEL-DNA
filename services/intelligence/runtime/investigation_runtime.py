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
    """


    def __init__(
        self,
        reasoner=None,
        recommendation_engine=None,
        orchestrator=None,
    ):


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
        Execute complete investigation.
        """


        context = RuntimeContext(
            case_id=case_id,
            evidence=evidence or [],
        )


        try:

            context.update_status(
                "running"
            )


            reasoning = (
                self.reasoner.reason(
                    context.to_dict()
                )
            )


            reasoning_result = (
                reasoning.to_dict()
                if hasattr(
                    reasoning,
                    "to_dict",
                )
                else reasoning
            )


            recommendations = (
                self.recommendation_engine.generate(
                    context.to_dict()
                )
            )


            orchestration = (
                self.orchestrator.investigate(
                    case_id=case_id,
                    artifacts=context.evidence,
                )
            )


            context.update_status(
                "completed"
            )


            return RuntimeResult(

                case_id=case_id,

                status="completed",

                investigation={
                    "analysis":
                        reasoning_result,
                },

                recommendations=(
                    recommendations.get(
                        "recommendations",
                        []
                    )
                    if isinstance(
                        recommendations,
                        dict,
                    )
                    else recommendations
                ),

                execution=(
                    orchestration.get(
                        "execution",
                        {}
                    )
                ),

                report=(
                    orchestration.get(
                        "report",
                        {}
                    )
                ),

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