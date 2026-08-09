"""
Runtime Gateway

Runtime execution boundary.

Responsible for:
- lifecycle control
- capability registration
- task submission
- execution routing
- runtime status
"""


from .task import Task

from .execution_result import (
    ExecutionResult,
)

from .runtime_intelligence_controller import (
    RuntimeIntelligenceController,
)



class RuntimeGateway:


    def __init__(
        self,
        controller=None,
    ):

        self.controller = (
            controller
            if controller is not None
            else RuntimeIntelligenceController()
        )

        self.handlers = {}

        self.running = False

        self.executions = 0

        self.initialized = True



    # =================================================
    # Lifecycle
    # =================================================

    def start(
        self,
    ):

        self.running = True


        if hasattr(
            self.controller,
            "start",
        ):

            self.controller.start()


        return True



    def stop(
        self,
    ):

        self.running = False


        if hasattr(
            self.controller,
            "stop",
        ):

            self.controller.stop()


        return False



    # =================================================
    # Registration
    # =================================================

    def register_handler(
        self,
        name,
        handler,
    ):

        self.handlers[name] = handler

        return True



    def register(
        self,
        name,
        handler,
    ):

        return self.register_handler(
            name,
            handler,
        )



    # =================================================
    # Submit
    # =================================================

    def submit(
        self,
        task,
    ):

        result = self.execute(
            task
        )


        return {

            "submitted":
                True,

            "result":
                result,

        }



    # =================================================
    # Execute
    # =================================================

    def execute(
        self,
        task,
    ):

        capability = None

        context = None



        if isinstance(
            task,
            Task,
        ):

            capability = getattr(
                task,
                "capability",
                None,
            )


            context = getattr(
                task,
                "payload",
                None,
            )



        elif isinstance(
            task,
            dict,
        ):

            capability = task.get(
                "capability"
            )

            context = task.get(
                "context",
                task.get(
                    "payload"
                )
            )



        else:

            capability = task



        handler = self.handlers.get(
            capability
        )


        if handler is not None:

            output = handler(
                context
            )


        else:

            output = self.controller.investigate(
                {

                    "capability":
                        capability,

                    "context":
                        context,

                }
            )



        self.executions += 1



        if isinstance(
            output,
            ExecutionResult,
        ):

            return output



        return ExecutionResult(
            success=True,
            output=output,
        )



    # =================================================
    # Status
    # =================================================

    def status(
        self,
    ):

        return {

            "initialized":
                self.initialized,

            "running":
                self.running,

            "healthy":
                True,

            "handlers":
                list(
                    self.handlers.keys()
                ),

            "executions":
                self.executions,

        }



RuntimeIntelligenceGateway = RuntimeGateway