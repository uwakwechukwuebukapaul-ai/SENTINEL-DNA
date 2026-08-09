"""
Runtime Execution Gateway

Security and access boundary for runtime execution.
"""

from __future__ import annotations

from typing import Any, Callable


class RuntimeAccessControl:
    """
    Minimal runtime permission registry.
    """

    def __init__(self):
        self.permissions: dict[str, set[str]] = {}

    def grant(
        self,
        principal: str,
        action: str,
    ) -> bool:
        if not principal or not action:
            return False

        self.permissions.setdefault(
            principal,
            set(),
        ).add(action)

        return True

    def revoke(
        self,
        principal: str,
        action: str,
    ) -> bool:
        actions = self.permissions.get(principal)

        if not actions or action not in actions:
            return False

        actions.remove(action)

        if not actions:
            del self.permissions[principal]

        return True

    def allowed(
        self,
        principal: str,
        action: str,
    ) -> bool:
        return (
            action
            in self.permissions.get(
                principal,
                set(),
            )
        )

    def status(self) -> dict:
        return {
            "principals": len(
                self.permissions
            ),
            "permissions": sum(
                len(actions)
                for actions in self.permissions.values()
            ),
        }


class RuntimeAuditLog:
    """
    Lightweight runtime audit store.
    """

    def __init__(self):
        self.entries: list[dict] = []

    def record(
        self,
        principal: str,
        action: str,
        task: Any = None,
        result: Any = None,
    ) -> bool:
        self.entries.append(
            {
                "principal": principal,
                "action": action,
                "task": task,
                "result": result,
            }
        )

        return True

    def count(self) -> int:
        return len(self.entries)

    def status(self) -> dict:
        return {
            "entries": len(self.entries),
        }


class RuntimeExecutionGateway:
    """
    Protected runtime execution boundary.

    Access:

        principal -> action -> execution

    Execution itself remains delegated to the
    RuntimeExecutionManager.
    """

    def __init__(
        self,
        execution=None,
        access=None,
        audit=None,
    ):
        from .runtime_execution_manager import (
            RuntimeExecutionManager,
        )

        self.execution = (
            execution
            if execution is not None
            else RuntimeExecutionManager()
        )

        self.access = (
            access
            if access is not None
            else RuntimeAccessControl()
        )

        self.audit = (
            audit
            if audit is not None
            else RuntimeAuditLog()
        )

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

    def register_handler(
        self,
        capability: str,
        handler: Callable,
    ) -> bool:
        return self.execution.register_handler(
            capability,
            handler,
        )

    def register(
        self,
        capability: str,
        handler: Callable,
    ) -> bool:
        return self.register_handler(
            capability,
            handler,
        )

    # =========================================================
    # Execution
    # =========================================================

    def execute(
        self,
        principal: str,
        action: str,
        task: Any,
    ):
        """
        Execute a task after access validation.

        Returns the native handler result.
        """

        if not self.running:
            self.start()

        # Always audit an attempted execution.
        self.audit.record(
            principal,
            action,
            task,
            None,
        )

        if not self.access.allowed(
            principal,
            action,
        ):
            return None

        capability = getattr(
            task,
            "capability",
            None,
        )

        if isinstance(task, dict):
            capability = task.get(
                "capability"
            )

        if not capability:
            return None

        result = self.execution.execute(
            capability,
            task,
        )

        # Some handlers expect payload rather than Task.
        # If the first execution did not resolve, try the
        # normalized payload through the manager.
        if result is None:
            payload = (
                task.get("payload")
                if isinstance(task, dict)
                else getattr(
                    task,
                    "payload",
                    None,
                )
            )

            result = self.execution.execute(
                capability,
                payload,
            )

        return result

    # =========================================================
    # Submission
    # =========================================================

    def submit(
        self,
        task: Any,
    ):
        if not self.running:
            self.start()

        return self.execution.submit(task)

    # =========================================================
    # Status
    # =========================================================

    def status(self) -> dict:
        return {
            "running": self.running,
            "access": self.access.status(),
            "execution": self.execution.status(),
            "audit": self.audit.status(),
        }