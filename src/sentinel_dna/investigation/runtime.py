from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from sentinel_dna.case_management.models import utc_now_iso
from sentinel_dna.investigation.context import InvestigationContext


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeTask:
    name: str
    handler: Callable[[InvestigationContext], Any]
    required: bool = False


class RuntimeTaskExecutor:
    def execute(self, context: InvestigationContext, tasks: list[RuntimeTask]) -> InvestigationContext:
        for task in tasks:
            started_at = utc_now_iso()
            if context.trace:
                context.trace.add_event(
                    task.name,
                    f"Started {task.name}",
                    {"required": task.required},
                )
            if context.replay:
                context.replay.add_event(
                    task.name,
                    f"Started {task.name}",
                    {"required": task.required},
                )
            try:
                task.handler(context)
                completed_at = utc_now_iso()
                audit_event = {
                    "stage": task.name,
                    "status": "success",
                    "started_at": started_at,
                    "completed_at": completed_at,
                }
                context.audit_trail.append(audit_event)
                context.task_results.append({"task": task.name, "status": "success"})
                if context.trace:
                    context.trace.add_event(task.name, f"Completed {task.name}", audit_event)
                if context.replay:
                    context.replay.add_event(task.name, f"Completed {task.name}", audit_event)
                logger.info(
                    "investigation_task_completed",
                    extra={"case_id": context.case_id, "stage": task.name, "required": task.required},
                )
            except Exception as exc:
                error = {
                    "stage": task.name,
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "required": task.required,
                }
                context.errors.append(error)
                completed_at = utc_now_iso()
                audit_event = {
                    "stage": task.name,
                    "status": "failed",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "error": error,
                }
                context.audit_trail.append(audit_event)
                context.task_results.append({"task": task.name, "status": "failed", "error": error})
                if context.trace:
                    context.trace.add_event(task.name, f"Failed {task.name}", audit_event)
                if context.replay:
                    context.replay.add_event(task.name, f"Failed {task.name}", audit_event)
                logger.exception(
                    "investigation_task_failed",
                    extra={"case_id": context.case_id, "stage": task.name, "required": task.required},
                )
                if task.required:
                    break
        return context
