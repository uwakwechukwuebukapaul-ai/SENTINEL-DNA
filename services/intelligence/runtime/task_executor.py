"""
Sentinel DNA Runtime Task Executor

Executes runtime tasks using registered
capability handlers.
"""

from __future__ import annotations

from typing import Any, Callable

from .task import Task


class RuntimeTaskExecutor:
    """
    Runtime task execution engine.
    """

    def __init__(self):

        self.handlers: dict[
            str,
            Callable
        ] = {}


    def register(
        self,
        capability: str,
        handler: Callable,
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
        Check whether capability exists.
        """

        return capability in self.handlers


    def execute(
        self,
        task: Task,
    ) -> Any:
        """
        Execute task.
        """

        handler = self.handlers.get(
            task.capability
        )


        if handler is None:

            task.fail(
                f"No handler for {task.capability}"
            )

            return None


        try:

            task.start()

            result = handler(
                task.payload
            )

            task.complete(
                result
            )

            return result


        except Exception as exc:

            task.fail(
                str(exc)
            )

            return None


    def clear(self) -> None:
        """
        Clear handlers.
        """

        self.handlers.clear()


    def status(self) -> dict:
        """
        Return executor state.
        """

        return {
            "handlers": list(
                self.handlers.keys()
            ),
            "count": len(
                self.handlers
            ),
        }