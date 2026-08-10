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
from services.intelligence.runtime.task import Task


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
# Investigation Result
# ============================================================


class InvestigationResult:
    """
    Stable investigation result contract.

    Compatibility fields intentionally preserved:

    - case_id
    - plan
    - plan_name
    - execution
    - status
    - results
    - errors
    - to_dict()
    """

    def __init__(
        self,
        case_id: str,
        plan: InvestigationPlan,
        execution: Optional[dict[str, Any]] = None,
        status: str = "completed",
    ) -> None:
        self.case_id = case_id
        self.plan = plan

        self.plan_name = getattr(
            plan,
            "plan_name",
            getattr(
                plan,
                "name",
                "Standard Security Investigation",
            ),
        )

        self.execution = execution
        self.status = status

        self.results: list[Any] = []
        self.errors: list[Any] = []

        if execution is not None:
            self.results.extend(
                self._extract_results(execution)
            )

            self._extract_errors(execution)

    @staticmethod
    def _extract_results(
        execution: Any,
    ) -> list[Any]:
        """
        Normalize execution output into the stable
        results list.
        """

        if isinstance(execution, dict):
            results = execution.get("results")

            if isinstance(results, list):
                return list(results)

        if execution is None:
            return []

        return [execution]

    def _extract_errors(
        self,
        execution: Any,
    ) -> None:
        """
        Extract execution errors.
        """

        if not isinstance(execution, dict):
            return

        errors = execution.get("errors")

        if isinstance(errors, list):
            self.errors.extend(
                str(error)
                for error in errors
                if error
            )

        error = execution.get("error")

        if error:
            self.errors.append(str(error))

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "plan_name": self.plan_name,
            "status": self.status,
            "results": list(self.results),
            "errors": list(self.errors),
            "execution": self.execution,
        }


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
        AI capability execution

    RuntimeTaskExecutor remains responsible only for executing
    runtime tasks.
    """

    def __init__(
        self,
        registry: Any = None,
        runtime: Any = None,
    ) -> None:
        self.registry = registry
        self.runtime = runtime

    # ========================================================
    # Context
    # ========================================================

    def create_context(
        self,
        investigation_id: str,
        artifacts: list[dict[str, Any]],
    ) -> InvestigationContext:
        """
        Create investigation execution context.
        """

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
        """
        Create the standard Sentinel DNA investigation plan.

        These are executable runtime capabilities.
        """

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
        """
        Create a real runtime Task.
        """

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
    # Capability Selection
    # ========================================================

    def _get_plan_capabilities(
        self,
        plan: InvestigationPlan,
    ) -> list[str]:
        """
        Extract executable capabilities from the plan.
        """

        capabilities = getattr(
            plan,
            "agents",
            [],
        )

        if not capabilities:
            return []

        return [
            str(capability)
            for capability in capabilities
            if capability
        ]

    # ========================================================
    # Runtime Capability Validation
    # ========================================================

    def _validate_capabilities(
        self,
        capabilities: list[str],
    ) -> list[str]:
        """
        Determine which planned capabilities are unavailable.
        """

        if self.runtime is None:
            return list(capabilities)

        missing: list[str] = []

        for capability in capabilities:
            if not self.runtime.available(capability):
                missing.append(capability)

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
        """
        Execute the complete investigation plan.

        Supported application contract:

            investigate(
                case_id=...,
                alert=...,
                artifacts=...,
            )

        The artifacts argument is intentionally supported here
        so InvestigationRuntime can pass evidence without having
        to manufacture a second orchestration contract.
        """

        alert_data = dict(alert or {})

        alert_data["case_id"] = case_id

        normalized_artifacts = [
            dict(item)
            if isinstance(item, dict)
            else {
                "type": "unknown",
                "value": item,
            }
            for item in (artifacts or [])
        ]

        # Preserve the alert as investigation evidence when
        # explicit artifacts were not supplied.
        if not normalized_artifacts and alert_data:
            normalized_artifacts = [
                {
                    "type": "alert",
                    "value": dict(alert_data),
                }
            ]

        plan = self.create_plan(
            case_id,
            alert_data,
        )

        context = self.create_context(
            investigation_id=(
                alert_data.get(
                    "investigation_id",
                    case_id,
                )
            ),
            artifacts=normalized_artifacts,
        )

        capabilities = self._get_plan_capabilities(
            plan
        )

        execution: dict[str, Any] = {
            "case_id": case_id,
            "alert": alert_data,
            "status": "pending",
            "capabilities": list(capabilities),
            "results": [],
            "errors": [],
            "tasks": [],
        }

        # ----------------------------------------------------
        # Runtime availability
        # ----------------------------------------------------

        if self.runtime is None:
            execution["status"] = "failed"
            execution["errors"].append(
                "Runtime task executor is not configured."
            )

            return InvestigationResult(
                case_id=case_id,
                plan=plan,
                execution=execution,
                status="failed",
            )

        missing = self._validate_capabilities(
            capabilities
        )

        if missing:
            execution["status"] = "failed"
            execution["errors"].append(
                "Missing runtime capabilities: "
                + ", ".join(missing)
            )

            return InvestigationResult(
                case_id=case_id,
                plan=plan,
                execution=execution,
                status="failed",
            )

        # ----------------------------------------------------
        # Execute planned capabilities
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
                task_result = self.runtime.execute(
                    task
                )

            except Exception as exc:
                task.error = str(exc)

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

                continue

            execution["tasks"].append(
                task.to_dict()
            )

            if task.error:
                execution["errors"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "error": task.error,
                    }
                )

                continue

            execution["results"].append(
                {
                    "capability": capability,
                    "task_id": task.task_id,
                    "result": task_result,
                }
            )

        # ----------------------------------------------------
        # Final execution state
        # ----------------------------------------------------

        if execution["errors"]:
            execution["status"] = "failed"
            status = "failed"
        else:
            execution["status"] = "completed"
            status = "completed"

        return InvestigationResult(
            case_id=case_id,
            plan=plan,
            execution=execution,
            status=status,
        )
