"""
Sentinel DNA Investigation Coordinator

High level investigation execution entry point.

Responsibilities:

- Create investigation context
- Build execution plan
- Dispatch runtime tasks
- Aggregate agent results
- Return orchestration outcome
"""

from typing import Any

from .investigation_context import InvestigationContext
from .investigation_plan import InvestigationPlan
from .orchestration_result import OrchestrationResult


class InvestigationCoordinator:
    """
    Coordinates investigation lifecycle execution.
    """

    def __init__(
        self,
        registry=None,
        runtime=None,
        orchestrator=None,
    ):

        self.registry = registry
        self.runtime = runtime
        self.orchestrator = orchestrator


    def create_context(
        self,
        investigation_id: str,
        evidence: list[Any] | None = None,
    ) -> InvestigationContext:
        """
        Build normalized investigation context.

        Converts incoming evidence into
        investigation IOCs.
        """

        evidence = evidence or []

        iocs = []

        for item in evidence:

            if isinstance(item, dict):

                indicator = item.get(
                    "indicator"
                )

                if indicator:

                    iocs.append(
                        indicator
                    )


        return InvestigationContext(
            investigation_id=investigation_id,
            case_id=investigation_id,
            evidence=evidence,
            iocs=iocs,
        )


    def create_plan(
        self,
        alert: dict,
    ) -> InvestigationPlan:
        """
        Create investigation execution plan.
        """

        return InvestigationPlan(
            investigation_id=alert.get(
                "case_id",
                "unknown",
            ),

            plan_name=(
                "Standard Security Investigation"
            ),

            agents=[
                "investigation_execution",
                "threat_intelligence",
                "ioc_enrichment",
            ],
        )


    def investigate(
        self,
        case_id: str,
        alert: dict,
    ) -> OrchestrationResult:
        """
        Execute investigation lifecycle.
        """

        context = self.create_context(
            case_id,
            [
                alert
            ],
        )


        plan = self.create_plan(
            alert
        )


        #
        # Preferred orchestration engine path
        #
        if self.orchestrator:

            return self.orchestrator.execute(
                plan,
                context,
            )


        #
        # Direct runtime execution path
        #
        if self.runtime:

            result = OrchestrationResult(
                plan_name=plan.plan_name,
                success=True,
            )


            for capability in plan.agents:

                task = self._create_task(
                    capability,
                    case_id,
                    alert,
                    context,
                )


                execution_result = (
                    self.runtime.execute(
                        task
                    )
                )


                if execution_result is not None:

                    result.add_agent_result(
                        capability,
                        execution_result,
                    )


                    result.agents_executed.append(
                        capability
                    )

                else:

                    result.add_error(
                        f"{capability} execution failed"
                    )


            if result.errors:

                result.success = False


            return result


        #
        # Runtime unavailable
        #
        result = OrchestrationResult(
            plan_name=plan.plan_name,
            success=False,
        )

        result.add_error(
            "Runtime unavailable"
        )

        return result



    def _create_task(
        self,
        capability: str,
        case_id: str,
        alert: dict,
        context: InvestigationContext,
    ):
        """
        Create runtime task.

        Kept isolated so future runtime
        scheduling can replace this layer.
        """

        from services.intelligence.runtime.task import Task


        return Task(
            capability=capability,

            payload={
                "case_id": case_id,
                "alert": alert,
                "context": context,
            },
        )