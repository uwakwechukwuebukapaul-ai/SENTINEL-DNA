"""
Sentinel DNA Runtime Execution Manager

Enterprise execution coordinator.

Responsibilities:

- runtime lifecycle
- capability registration
- task submission
- task execution
- result normalization
- pipeline management
- metrics
- health reporting
"""

from __future__ import annotations

from typing import Any

from .execution_result import ExecutionResult


class RuntimeExecutionPipeline:
    """
    Runtime execution queue/pipeline.
    """

    def __init__(
        self,
        manager: "RuntimeExecutionManager",
    ) -> None:

        self.manager = manager

        self.queue: list[Any] = []


    def submit(
        self,
        task: Any,
    ):

        self.queue.append(task)

        return self.manager.execute(
            task
        )


    def size(
        self,
    ) -> int:

        return len(
            self.queue
        )


    def clear(
        self,
    ):

        self.queue.clear()

        return True



class RuntimeExecutionManager:
    """
    Core Sentinel DNA runtime execution manager.
    """

    def __init__(
        self,
    ) -> None:

        self.running = False


        self.handlers: dict[str, Any] = {}


        self.metrics = type(
            "RuntimeMetrics",
            (),
            {}
        )()

        self.metrics.executions = 0

        self.metrics.failures = 0

        self.metrics.submissions = 0



        self.pipeline = RuntimeExecutionPipeline(
            self
        )


        # Compatibility layer
        self.workers = type(
            "RuntimeWorkers",
            (),
            {}
        )()

        self.workers.executor = self



    # ==================================================
    # LIFECYCLE
    # ==================================================

    def start(
        self,
    ) -> bool:

        self.running = True

        return True



    def stop(
        self,
    ) -> bool:

        self.running = False

        return True



    def clear(
        self,
    ) -> bool:

        self.handlers.clear()

        self.pipeline.clear()


        self.metrics.executions = 0

        self.metrics.failures = 0

        self.metrics.submissions = 0


        return True



    # ==================================================
    # REGISTRATION
    # ==================================================

    def register_handler(
        self,
        capability: str,
        handler,
    ) -> bool:


        if not capability:

            return False


        if not callable(handler):

            return False


        self.handlers[capability] = handler


        return True



    def register(
        self,
        capability,
        handler,
    ):

        return self.register_handler(
            capability,
            handler,
        )



    def exists(
        self,
        capability,
    ):

        return capability in self.handlers



    # ==================================================
    # EXECUTION
    # ==================================================

    def execute(
        self,
        *args,
    ) -> ExecutionResult:


        if len(args) == 1:

            task = args[0]

            capability = getattr(
                task,
                "capability",
                None,
            )


        elif len(args) == 2:

            capability = args[0]

            task = args[1]


        else:

            return ExecutionResult.failure(
                "Invalid execution arguments."
            )



        if not capability:

            self.metrics.failures += 1

            return ExecutionResult.failure(
                "Missing capability."
            )



        handler = self.handlers.get(
            capability
        )



        if handler is None:

            self.metrics.failures += 1

            return ExecutionResult.failure(
                f"No handler registered for {capability}"
            )



        try:

            output = handler(
                task
            )


            self.metrics.executions += 1


            return ExecutionResult.ok(
                result=output,
                output=output,
                data=output,
            )



        except TypeError:

            try:

                output = handler(
                    getattr(
                        task,
                        "payload",
                        task,
                    )
                )


                self.metrics.executions += 1


                return ExecutionResult.ok(
                    result=output,
                    output=output,
                    data=output,
                )


            except Exception as exc:


                self.metrics.failures += 1


                return ExecutionResult.failure(
                    str(exc)
                )



        except Exception as exc:


            self.metrics.failures += 1


            return ExecutionResult.failure(
                str(exc)
            )



    # ==================================================
    # SUBMISSION
    # ==================================================

    def submit(
        self,
        task,
    ):


        self.metrics.submissions += 1


        return self.pipeline.submit(
            task
        )



    # ==================================================
    # STATUS
    # ==================================================

    def status(
        self,
    ):

        return {

            "running":
                self.running,


            "handlers":
                list(
                    self.handlers.keys()
                ),


            "workers":
                {
                    "executor": True
                },


            "pipeline":
                {
                    "size":
                        self.pipeline.size()
                },


            "metrics":
                {

                    "executions":
                        self.metrics.executions,


                    "failures":
                        self.metrics.failures,


                    "submissions":
                        self.metrics.submissions,

                },

        }