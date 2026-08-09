"""
Runtime Control Plane

Coordinates runtime lifecycle, execution and events.
"""

from __future__ import annotations

from typing import Any, Callable

from .runtime_execution_manager import (
    RuntimeExecutionManager,
)


class RuntimeEventBus:
    """
    Small in-process event bus used by the runtime control plane.
    """

    def __init__(self):
        self.handlers: dict[str, list[Callable]] = {}

    def register(
        self,
        event: str,
        handler: Callable,
    ) -> bool:
        if not event or not callable(handler):
            return False

        self.handlers.setdefault(
            event,
            [],
        ).append(handler)

        return True

    def unregister(
        self,
        event: str,
        handler: Callable,
    ) -> bool:
        handlers = self.handlers.get(event)

        if not handlers or handler not in handlers:
            return False

        handlers.remove(handler)

        if not handlers:
            del self.handlers[event]

        return True

    def emit(
        self,
        event: str,
        data: Any = None,
    ) -> bool:
        for handler in list(
            self.handlers.get(event, [])
        ):
            handler(data)

        return True

    def count(self) -> int:
        return sum(
            len(handlers)
            for handlers in self.handlers.values()
        )

    def status(self) -> dict:
        return {
            "events": len(self.handlers),
            "handlers": self.count(),
        }


class RuntimeControlPlane:
    """
    Runtime control boundary.

    Exposes lifecycle, submission, registration and event
    management while delegating execution to the manager.
    """

    def __init__(
        self,
        execution=None,
    ):
        self.execution = (
            execution
            if execution is not None
            else RuntimeExecutionManager()
        )

        self.events = RuntimeEventBus()

        self.running = False

    # =========================================================
    # Lifecycle
    # =========================================================

    def start(self) -> bool:
        self.running = True
        self.execution.start()
        return True

    def stop(self) -> bool:
        self.running = False
        self.execution.stop()
        return True

    # =========================================================
    # Registration
    # =========================================================

    def register(
        self,
        capability: str,
        handler: Callable,
    ) -> bool:
        return self.execution.register(
            capability,
            handler,
        )

    def register_handler(
        self,
        capability: str,
        handler: Callable,
    ) -> bool:
        return self.register(
            capability,
            handler,
        )

    # =========================================================
    # Submission
    # =========================================================

    def submit(
        self,
        task: Any,
    ):
        """
        Submit a task through the execution manager.

        The execution result is deliberately returned directly
        instead of being discarded.
        """

        if not self.running:
            self.start()

        result = self.execution.submit(task)

        if result is not None:
            self.events.emit(
                "execution.completed",
                result,
            )
        else:
            self.events.emit(
                "execution.failed",
                task,
            )

        return result

    # =========================================================
    # Events
    # =========================================================

    def emit(
        self,
        event: str,
        data: Any = None,
    ) -> bool:
        return self.events.emit(
            event,
            data,
        )

    # =========================================================
    # Status
    # =========================================================

    def status(self) -> dict:
        return {
            "running": self.running,
            "execution": self.execution.status(),
            "events": self.events.status(),
            "health": {
                "healthy": True,
                "running": self.running,
            },
        }