"""
Sentinel DNA Investigation Coordinator.

Canonical application-level investigation coordinator.

Responsibilities:

- Investigation planning
- Investigation context creation
- Runtime task creation
- Runtime capability validation
- Runtime task execution
- Stable investigation result generation

Architecture:

API
 |
 v
InvestigationRuntime
 |
 v
InvestigationCoordinator
 |
 v
InvestigationPlan
 |
 v
Runtime Task(s)
 |
 v
RuntimeTaskExecutor
 |
 v
AI Investigation Capabilities

The coordinator owns workflow coordination.

RuntimeTaskExecutor owns task execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


from .investigation_plan import InvestigationPlan
from .investigation_orchestrator import InvestigationOrchestrator

from services.intelligence.runtime.task import Task

from services.intelligence.investigation.investigation_result import (
    InvestigationResult,
)


# ============================================================
# Investigation Context
# ============================================================


@dataclass
class InvestigationContext:
    """
    Coordinator-level investigation execution context.
    """

    investigation_id: str

    artifacts: list[dict[str, Any]] = field(
        default_factory=list
    )


# ============================================================
# Investigation Coordinator
# ============================================================


class InvestigationCoordinator:
    """
    Canonical application-level investigation coordinator.

    Coordinates:

        Investigation planning
              |
              v
        Runtime task creation
              |
              v
        Runtime task execution
              |
              v
        AI investigation capabilities


    RuntimeTaskExecutor owns execution.

    Coordinator owns workflow.
    """


    def __init__(
        self,
        registry: Any = None,
        runtime: Any = None,
        orchestrator: Any = None,
    ) -> None:

        self.registry = registry
        self.runtime = runtime
        self.orchestrator = (
            orchestrator
            if orchestrator is not None
            else InvestigationOrchestrator()
        )


    # ========================================================
    # Context
    # ========================================================


    def create_context(
        self,
        investigation_id: str,
        artifacts: list[dict[str, Any]],
    ) -> InvestigationContext:

        return InvestigationContext(
            investigation_id=investigation_id,
            artifacts=list(artifacts),
        )


    # ========================================================
    # Planning
    # ========================================================


    def create_plan(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationPlan:

        return InvestigationPlan(
            case_id=case_id,
            name="Standard Security Investigation",
            plan_name="Standard Security Investigation",
            agents=[
                "investigation_execution",
                "threat_intelligence",
                "ioc_enrichment",
            ],
        )


    # ========================================================
    # Runtime Task Creation
    # ========================================================


    def _create_runtime_task(
        self,
        case_id: str,
        alert: dict[str, Any],
        plan: InvestigationPlan,
        capability: str,
        context: InvestigationContext,
    ) -> Task:

        return Task(
            capability=capability,
            payload={
                "case_id": case_id,
                "alert": alert,
                "plan": plan,
                "context": context,
                "investigation_id": context.investigation_id,
                "artifacts": list(context.artifacts),
            },
        )


    # ========================================================
    # Capability Handling
    # ========================================================


    def _get_plan_capabilities(
        self,
        plan: InvestigationPlan,
    ) -> list[str]:

        capabilities = getattr(
            plan,
            "agents",
            [],
        )

        return [
            str(capability)
            for capability in capabilities
            if capability
        ]


    def _validate_capabilities(
        self,
        capabilities: list[str],
    ) -> list[str]:

        if self.runtime is None:
            return list(capabilities)

        missing = []

        for capability in capabilities:

            if not self.runtime.available(
                capability
            ):
                missing.append(
                    capability
                )

        return missing


    # ========================================================
    # Investigation Execution
    # ========================================================


    def investigate(
        self,
        case_id: str,
        alert: Optional[dict[str, Any]] = None,
        artifacts: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> InvestigationResult:


        alert_data = dict(
            alert or {}
        )

        alert_data["case_id"] = case_id


        normalized_artifacts = []

        for item in artifacts or []:

            if isinstance(item, dict):

                normalized_artifacts.append(
                    dict(item)
                )

            else:

                normalized_artifacts.append(
                    {
                        "type": "unknown",
                        "value": item,
                    }
                )


        if not normalized_artifacts:

            normalized_artifacts.append(
                {
                    "type": "alert",
                    "value": alert_data,
                }
            )

        workflow = self.orchestrator.investigate(
            case_id=case_id,
            artifacts=normalized_artifacts,
            alert=alert_data,
            **kwargs,
        )

        plan = self.create_plan(
            case_id,
            alert_data,
        )


        context = self.create_context(
            investigation_id=alert_data.get(
                "investigation_id",
                case_id,
            ),
            artifacts=normalized_artifacts,
        )


        capabilities = self._get_plan_capabilities(
            plan
        )


        execution = {
            "case_id": case_id,
            "status": "pending",
            "capabilities": capabilities,
            "results": [],
            "errors": [],
            "tasks": [],
            "workflow": workflow,
        }


        # ----------------------------------------------------
        # Runtime validation
        # ----------------------------------------------------


        if self.runtime is None:

            return InvestigationResult(
                success=False,
                status="failed",
                message="Runtime task executor is not configured.",
                error="Runtime task executor is not configured.",
                case_id=case_id,
                plan=plan,
                plan_name=plan.plan_name,
                execution=execution,
                results=[],
                artifacts=normalized_artifacts,
                findings=[],
                intelligence={
                    "workflow": workflow,
                },
                errors=[
                    "Runtime task executor is not configured."
                ],
            )


        missing = self._validate_capabilities(
            capabilities
        )


        if missing:

            error_message = (
                "Missing runtime capabilities: "
                + ", ".join(missing)
            )

            return InvestigationResult(
                success=False,
                status="failed",
                message="Missing runtime capabilities.",
                error=error_message,
                case_id=case_id,
                plan=plan,
                plan_name=plan.plan_name,
                execution=execution,
                results=[],
                artifacts=normalized_artifacts,
                findings=[],
                intelligence={
                    "workflow": workflow,
                },
                errors=[
                    error_message
                ],
            )


        # ----------------------------------------------------
        # Execute capabilities
        # ----------------------------------------------------


        for capability in capabilities:

            task = self._create_runtime_task(
                case_id=case_id,
                alert=alert_data,
                plan=plan,
                capability=capability,
                context=context,
            )


            try:

                result = self.runtime.execute(
                    task
                )


                execution["results"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "result": result,
                    }
                )


            except Exception as exc:

                execution["errors"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "error": str(exc),
                    }
                )


            execution["tasks"].append(
                task.to_dict()
            )


        success = not bool(
            execution["errors"]
        )


        execution["status"] = (
            "completed"
            if success
            else "failed"
        )


        return InvestigationResult(
            success=success,
            status=execution["status"],
            message=(
                "Investigation completed."
                if success
                else "Investigation failed."
            ),
            error=(
                None
                if success
                else str(
                    execution["errors"]
                )
            ),
            case_id=case_id,
            plan=plan,
            plan_name=getattr(
                plan,
                "plan_name",
                "Standard Security Investigation",
            ),
            execution=execution,
            results=list(
                execution["results"]
            ),
            errors=list(
                execution["errors"]
            ),
            artifacts=normalized_artifacts,
            findings=list(
                execution["results"]
            ),
            intelligence={
                "plan_name": getattr(
                    plan,
                    "plan_name",
                    "Standard Security Investigation",
                ),
                "capabilities": capabilities,
                "execution": execution,
                "workflow": workflow,
            },
        )
