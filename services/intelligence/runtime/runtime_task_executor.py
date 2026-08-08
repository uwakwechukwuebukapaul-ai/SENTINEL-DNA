"""
Sentinel DNA Runtime Task Executor

Core execution engine for AI agent capabilities.

Responsibilities:

- Register capability handlers
- Execute runtime tasks
- Track execution metrics
- Manage task lifecycle
"""

from __future__ import annotations

from typing import Any, Callable

from .task import Task, TaskStatus


class RuntimeTaskExecutor:
    """
    Enterprise runtime execution engine.
    """


    def __init__(self) -> None:

        self.handlers: dict[
            str,
            Callable[[dict[str, Any]], Any],
        ] = {}

        self.executed = 0
        self.completed = 0
        self.failed = 0



    def register(
        self,
        capability: str,
        handler: Callable[
            [dict[str, Any]],
            Any,
        ],
    ) -> None:
        """
        Register capability handler.
        """

        self.handlers[
            capability
        ] = handler



    def execute(
        self,
        task: Task,
    ) -> Any:
        """
        Execute runtime task.
        """

        self.executed += 1


        handler = self.handlers.get(
            task.capability
        )


        if handler is None:

            task.status = TaskStatus.FAILED

            task.error = (
                f"No handler registered "
                f"for capability: "
                f"{task.capability}"
            )

            self.failed += 1

            return None



        try:

            result = handler(
                task.payload
            )


            task.result = result

            task.status = (
                TaskStatus.COMPLETED
            )

            self.completed += 1


            return result



        except Exception as exc:

            import traceback


            task.status = (
                TaskStatus.FAILED
            )


            task.error = str(exc)


            self.failed += 1


            traceback.print_exc()


            return None



    def status(
        self,
    ) -> dict[str, Any]:
        """
        Runtime health status.
        """

        return {

            "handlers":
                list(
                    self.handlers.keys()
                ),

            "executed":
                self.executed,

            "completed":
                self.completed,

            "failed":
                self.failed,

        }