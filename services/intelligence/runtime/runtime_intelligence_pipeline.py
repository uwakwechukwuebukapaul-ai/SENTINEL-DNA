"""
Runtime Intelligence Pipeline

Capability execution router.
"""


class RuntimeIntelligencePipeline:

    def __init__(
        self,
        runtime=None,
    ):

        if runtime is None:

            try:
                from .runtime_intelligence_runtime import (
                    RuntimeIntelligenceRuntime,
                )

                runtime = RuntimeIntelligenceRuntime()

            except Exception:
                runtime = None


        self.runtime = runtime

        self.router = {}

        self._executions = []



    # -----------------------------
    # Properties
    # -----------------------------

    @property
    def count(self):

        return len(
            self.router
        )


    @property
    def executions(self):

        return len(
            self._executions
        )



    # -----------------------------
    # Registration
    # -----------------------------

    def register(
        self,
        name,
        handler,
    ):

        self.router[name] = handler

        return True



    def available(
        self,
        name=None,
    ):

        if name is None:

            return list(
                self.router.keys()
            )


        return name in self.router



    # -----------------------------
    # Execution
    # -----------------------------

    def execute(
        self,
        capability,
        context=None,
    ):


        handler = self.router.get(
            capability
        )


        if handler is None:

            return None



        result = handler(
            context
        )


        investigation_id = None


        if hasattr(
            context,
            "investigation_id",
        ):

            investigation_id = (
                context.investigation_id
            )


        elif isinstance(
            context,
            dict,
        ):

            investigation_id = (
                context.get(
                    "investigation_id"
                )
            )


        response = {

            "id":
                investigation_id,

            "success":
                True,

            "result":
                result,

        }


        self._executions.append(
            response
        )


        return response



    # -----------------------------
    # Clear
    # -----------------------------

    def clear(self):

        self.router.clear()

        self._executions.clear()

        return True



    # -----------------------------
    # Status
    # -----------------------------

    def status(self):

        return {

            "healthy":
                True,

            "router":
                list(
                    self.router.keys()
                ),

            "count":
                self.count,

            "executions":
                self.executions,

        }