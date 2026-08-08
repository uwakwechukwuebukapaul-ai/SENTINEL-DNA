"""
Sentinel DNA Autonomous Investigation Orchestrator

Connects intelligence engines into
a complete investigation workflow.
"""

from __future__ import annotations

from typing import Any


from .investigation_context import (
    InvestigationContext,
)


from .investigation_plan import (
    InvestigationPlan,
)



class InvestigationOrchestrator:
    """
    Executes AI investigation workflow.
    """


    def create_plan(
        self,
        case_id: str,
    ) -> InvestigationPlan:

        plan = InvestigationPlan(
            case_id=case_id
        )


        for stage in [

            "evidence_collection",
            "mitre_mapping",
            "risk_analysis",
            "confidence_analysis",
            "recommendation_generation",
            "timeline_generation",

        ]:

            plan.add_stage(
                stage
            )


        return plan



    def investigate(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationContext:


        context = InvestigationContext(
            case_id=case_id,
            alert=alert,
        )


        plan = self.create_plan(
            case_id
        )


        context.add_result(
            "plan",
            plan.to_dict(),
        )


        return context