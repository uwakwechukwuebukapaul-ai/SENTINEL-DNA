"""
Sentinel DNA Runtime Task Executor

Canonical enterprise runtime execution engine.

Responsibilities:

- Register capability handlers
- Execute runtime tasks
- Track execution metrics
- Report runtime status
- Handle execution failures
- Maintain compatibility with legacy runtime APIs

Architecture:

InvestigationCoordinator
    -> InvestigationOrchestrator
        -> RuntimeTaskExecutor
            -> registered capability handler
                -> agent/service execution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .task import Task
from services.observability import ObservabilityService
import time
from uuid import uuid4


TaskHandler = Callable[[dict[str, Any]], Any]


class RuntimeExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class RuntimeTaskFailure:
    """Safe, serializable failure returned for non-success execution."""

    task_id: str
    capability: str
    status: RuntimeExecutionStatus
    error_code: str
    error: str
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "capability": self.capability,
            "status": self.status.value,
            "error_code": self.error_code,
            "error": self.error,
            "retryable": self.retryable,
            "metadata": dict(self.metadata),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


@dataclass
class RuntimeTaskExecutor:
    """
    Canonical Sentinel DNA runtime task execution engine.

    The executor owns capability registration and task execution
    state for a runtime instance.

    A handler receives the task payload and returns the execution
    result.
    """

    handlers: dict[str, TaskHandler] = field(
        default_factory=dict
    )

    executed: int = 0

    failed: int = 0

    @staticmethod
    def new_execution_id() -> str:
        """Create an execution envelope ID; safe for future worker handoff."""
        return str(uuid4())

    # ------------------------------------------------------------------
    # Capability registration
    # ------------------------------------------------------------------

    def register(
        self,
        capability: str,
        handler: TaskHandler,
    ) -> None:
        """
        Register a handler for a runtime capability.

        Re-registering a capability intentionally replaces the
        existing handler. This allows application bootstrap to
        refresh capability implementations safely.
        """

        if not isinstance(capability, str):
            raise TypeError(
                "capability must be a string."
            )

        capability = capability.strip()

        if not capability:
            raise ValueError(
                "capability must not be empty."
            )

        if not callable(handler):
            raise TypeError(
                "handler must be callable."
            )

        self.handlers[capability] = handler

    # ------------------------------------------------------------------
    # Capability discovery
    # ------------------------------------------------------------------

    def available(
        self,
        capability: str,
    ) -> bool:
        """
        Check whether a capability has a registered handler.
        """

        return capability in self.handlers

    def capabilities(self) -> list[str]:
        """
        Return all registered runtime capabilities.
        """

        return list(self.handlers.keys())

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def execute(
        self,
        task: Task,
    ) -> Any:
        """
        Execute a runtime task through its registered capability.

        Lifecycle:

        PENDING
            -> RUNNING
            -> COMPLETED

        or:

        PENDING
            -> RUNNING
            -> FAILED

        Unknown capabilities fail deterministically and are counted
        as failed executions.
        """

        if not isinstance(task, Task):
            raise TypeError(
                "task must be a Task instance."
            )

        observer = ObservabilityService()
        started = time.perf_counter()
        context = task.payload.get("context")
        correlation_id = task.payload.get("correlation_id") or getattr(context, "correlation_id", None)
        event_context = {"correlation_id": correlation_id} if correlation_id else {}
        observer.event("AGENT_STARTED", case_id=task.payload.get("case_id"), agent=task.capability, **event_context)

        if not task.status.can_execute() or (task.status.value == "pending" and not task.can_retry):
            task.mark_blocked("Task is not executable in its current state")
            self.failed += 1
            failure = RuntimeTaskFailure(
                task.task_id,
                task.capability,
                RuntimeExecutionStatus.BLOCKED,
                "task_not_executable",
                "Task is not executable in its current state",
                retryable=False,
                metadata={"lifecycle_status": task.status.value, "execution_id": task.execution_id, "attempt": task.attempt},
            )
            observer.event("AGENT_BLOCKED", case_id=task.payload.get("case_id"), agent=task.capability, status="blocked", duration_ms=round((time.perf_counter()-started)*1000, 2), **event_context)
            return failure

        handler = self.handlers.get(
            task.capability
        )

        if handler is None:
            task.mark_unavailable("Capability is not registered")

            self.failed += 1
            failure = RuntimeTaskFailure(
                task.task_id,
                task.capability,
                RuntimeExecutionStatus.UNAVAILABLE,
                "capability_unavailable",
                "Capability is not registered",
                retryable=False,
                metadata={"execution_id": task.execution_id, "attempt": task.attempt},
            )
            observer.event("AGENT_UNAVAILABLE", case_id=task.payload.get("case_id"), agent=task.capability, status="unavailable", duration_ms=round((time.perf_counter()-started)*1000, 2), errors=[failure.error_code], **event_context)

            return failure

        task.start()

        try:
            result = handler(
                task.payload
            )

            task.complete(
                result
            )

            self.executed += 1
            observer.event("AGENT_COMPLETED", case_id=task.payload.get("case_id"), agent=task.capability, status="completed", duration_ms=round((time.perf_counter()-started)*1000, 2), **event_context)

            return result

        except Exception as exc:
            safe_type = type(exc).__name__
            task.fail(safe_type)

            self.failed += 1
            failure = RuntimeTaskFailure(
                task.task_id,
                task.capability,
                RuntimeExecutionStatus.FAILED,
                "handler_exception",
                "Capability handler failed",
                retryable=True,
                metadata={"exception_type": safe_type, "execution_id": task.execution_id, "attempt": task.attempt},
            )
            observer.event("AGENT_FAILED", case_id=task.payload.get("case_id"), agent=task.capability, status="failed", duration_ms=round((time.perf_counter()-started)*1000, 2), errors=[safe_type], **event_context)

            return failure

    # ------------------------------------------------------------------
    # Runtime management
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """
        Clear all registered capability handlers.

        Execution metrics are intentionally preserved.
        """

        self.handlers.clear()

    # ------------------------------------------------------------------
    # Metrics / status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """
        Return runtime execution status.
        """

        capabilities = self.capabilities()

        return {
            "handlers": capabilities,
            "registered_handlers": len(
                capabilities
            ),
            "executed": self.executed,
            "failed": self.failed,
            "success": self.executed,
            "available": capabilities,
            "contract": {
                "task_states": ["PENDING", "RUNNING", "SUCCESS", "FAILED", "UNAVAILABLE", "BLOCKED"],
                "durability": "in_process_boundary",
                "worker_ready": True,
            },
        }
