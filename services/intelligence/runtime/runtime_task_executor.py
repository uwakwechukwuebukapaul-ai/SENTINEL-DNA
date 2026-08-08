"""
Sentinel DNA Runtime Task Executor

Enterprise execution engine.

Responsibilities:

- Register capability handlers
- Execute runtime tasks
- Track execution metrics
- Report runtime status
- Handle failures
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .task import Task


TaskHandler = Callable[[dict[str, Any]], Any]


@dataclass
class RuntimeTaskExecutor:
    """
    Runtime task execution engine.
    """

    handlers: dict[str, TaskHandler] = field(
        default_factory=dict
    )

    executed: int = 0

    failed: int = 0


    def register(
        self,
        capability: str,
        handler: TaskHandler,
    ) -> None:
        """
        Register capability handler.
        """

        self.handlers[capability] = handler


    def available(
        self,
        capability: str,
    ) -> bool:
        """
        Check capability availability.
        """

        return capability in self.handlers


    def execute(
        self,
        task: Task,
    ) -> Any:
        """
        Execute task.
        """

        if not self.available(
            task.capability
        ):

            task.fail(
                f"No handler registered for {task.capability}"
            )

            self.failed += 1

            return None


        task.start()


        try:

            handler = self.handlers[
                task.capability
            ]

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


    def capabilities(self) -> list[str]:
        """
        List registered capabilities.
        """

        return list(
            self.handlers.keys()
        )


    def status(self) -> dict[str, Any]:
        """
        Runtime execution status.
        """

        return {
            "handlers": list(
                self.handlers.keys()
            ),
            "registered_handlers": len(
                self.handlers
            ),
            "executed": self.executed,
            "failed": self.failed,
            "available": list(
                self.handlers.keys()
            ),
        }