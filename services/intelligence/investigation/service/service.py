"""
Sentinel DNA Unified Investigation Service.

High-level orchestration service that combines:

Evidence
↓
AI Investigator Runtime
↓
Decision Intelligence
↓
Investigation Result

This layer acts as the service boundary between
intelligence engines and future API interfaces.
"""

from typing import Any

from ..runtime import (
    AIInvestigatorRuntime,
)

from ..decision.engine import (
    InvestigationDecisionEngine,
)

from ...models import (
    InvestigationServiceResult,
)


class UnifiedInvestigationService:
    """
    Unified investigation execution service.

    Coordinates autonomous investigation workflow.
    """

    def __init__(self):

        self.runtime = (
            AIInvestigatorRuntime()
        )

        self.decision_engine = (
            InvestigationDecisionEngine()
        )


    def investigate(
        self,
        case_id: str,
        evidence: Any,
    ) -> InvestigationServiceResult:
        """
        Execute complete investigation workflow.
        """

        runtime_result = (
            self.runtime.investigate(
                case_id,
                evidence,
            )
        )


        investigation_data = (
            runtime_result.to_dict()
            if hasattr(
                runtime_result,
                "to_dict",
            )
            else runtime_result
        )


        decision = (
            self.decision_engine.evaluate(
                investigation_data
            )
        )


        decision_data = (
            decision.to_dict()
            if hasattr(
                decision,
                "to_dict",
            )
            else decision
        )


        return InvestigationServiceResult(

            case_id=case_id,

            status="completed",

            investigation={
                "runtime": investigation_data,
                "decision": decision_data,
            },

            metadata={

                "service":
                    "unified_investigation_service",

                "components": [

                    "ai_investigator_runtime",

                    "decision_intelligence",

                ],

                "risk":
                    investigation_data.get(
                        "metadata",
                        {}
                    ).get(
                        "risk",
                        "unknown",
                    ),

            },
        )