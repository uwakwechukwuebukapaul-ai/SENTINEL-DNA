from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sentinel_dna.case_management.models import utc_now_iso
from sentinel_dna.investigation.context import InvestigationContext


@dataclass(frozen=True)
class RuntimeTask:
    name: str
    handler: Callable[[InvestigationContext], Any]
    required: bool = False


class RuntimeTaskExecutor:
    def execute(self, context: InvestigationContext, tasks: list[RuntimeTask]) -> InvestigationContext:
        for task in tasks:
            started_at = utc_now_iso()
            try:
                task.handler(context)
                context.audit_trail.append(
                    {
                        "stage": task.name,
                        "status": "success",
                        "started_at": started_at,
                        "completed_at": utc_now_iso(),
                    }
                )
                context.task_results.append({"task": task.name, "status": "success"})
            except Exception as exc:
                error = {
                    "stage": task.name,
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "required": task.required,
                }
                context.errors.append(error)
                context.audit_trail.append(
                    {
                        "stage": task.name,
                        "status": "failed",
                        "started_at": started_at,
                        "completed_at": utc_now_iso(),
                        "error": error,
                    }
                )
                context.task_results.append({"task": task.name, "status": "failed", "error": error})
                if task.required:
                    break
        return context
