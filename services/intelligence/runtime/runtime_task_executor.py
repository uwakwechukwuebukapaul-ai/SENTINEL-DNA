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
from typing import Any, Callable

from .task import Task


TaskHandler = Callable[[dict[str, Any]], Any]


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

        handler = self.handlers.get(
            task.capability
        )

        if handler is None:
            task.fail(
                f"No handler registered for {task.capability}"
            )

            self.failed += 1

            return None

        task.start()

        try:
            result = handler(
                task.payload
            )

            task.complete(
                result
            )

            self.executed += 1

            return result

        except Exception as exc:
            task.fail(
                str(exc)
            )

            self.failed += 1

            return None

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
            "available": capabilities,
        }
