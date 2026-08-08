"""
Sentinel DNA Runtime Task Executor

Executes investigation tasks through registered capability handlers.
"""

from typing import Any

from ...task import Task, TaskStatus



class RuntimeTaskExecutor:
    """
    Runtime execution engine for investigation tasks.
    """


    def __init__(self):

        self.handlers: dict[str, Any] = {}



    def register(
        self,
        capability: str,
        handler: Any,
    ):

        self.handlers[capability] = handler



    def unregister(
        self,
        capability: str,
    ):

        self.handlers.pop(
            capability,
            None,
        )



    def status(self):

        return {
            "handlers": list(
                self.handlers.keys()
            )
        }



    def execute(
        self,
        task: Task,
    ):


        handler = self.handlers.get(
            task.capability
        )


        if handler is None:

            task.status = TaskStatus.FAILED

            task.error = (
                f"Agent not found: "
                f"{task.capability}"
            )

            return None



        try:

            task.status = TaskStatus.RUNNING


            result = handler(
                task.payload
            )


            task.status = TaskStatus.COMPLETED

            task.result = result


            return result



        except Exception as exc:

            task.status = TaskStatus.FAILED

            task.error = str(exc)

            return None