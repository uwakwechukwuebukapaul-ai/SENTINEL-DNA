"""
Sentinel DNA Runtime Orchestration Service

Coordinates:

- capability registration
- workflow submission
- workflow execution
- runtime lifecycle
"""

from .runtime_execution_manager import (
    RuntimeExecutionManager,
)


class RuntimeDispatcher:

    def __init__(
        self,
    ):

        self.handlers = {}

    def register(
        self,
        capability,
        handler,
    ):

        self.handlers[capability] = handler

        return True


    def exists(
        self,
        capability,
    ):

        return capability in self.handlers


    def available(
        self,
        capability,
    ):

        return self.exists(
            capability
        )


    def execute(
        self,
        capability,
        payload=None,
    ):

        handler = self.handlers.get(
            capability
        )

        if handler is None:

            return None


        return handler(
            payload
        )



class RuntimePipeline:

    def __init__(
        self,
    ):

        self.dispatcher = RuntimeDispatcher()

        self.tasks = []

        self.pipeline = self


    def add(
        self,
        task,
    ):

        self.tasks.append(
            task
        )

        return True


    def size(
        self,
    ):

        return len(
            self.tasks
        )


    def clear(
        self,
    ):

        self.tasks.clear()

        return True



class RuntimeControlPlane:

    def __init__(
        self,
    ):

        self.running = False

        self.pipeline = RuntimePipeline()

        self.execution = self.pipeline



    def start(
        self,
    ):

        self.running = True

        return True



    def stop(
        self,
    ):

        self.running = False

        return True



    def status(
        self,
    ):

        return {

            "running":
                self.running,

            "pipeline":
                {
                    "size":
                        self.pipeline.size()
                },

        }



class RuntimeOrchestrationService:

    def __init__(
        self,
        manager=None,
    ):

        self.manager = (

            manager

            if manager is not None

            else RuntimeExecutionManager()

        )


        self.control_plane = RuntimeControlPlane()


        self.last_workflow = None

        self.workflows = 0

        self.running = False



    # ==================================================
    # Lifecycle
    # ==================================================

    def start(
        self,
    ):

        self.running = True

        self.control_plane.start()

        self.manager.start()

        return True



    def stop(
        self,
    ):

        self.running = False

        self.control_plane.stop()

        self.manager.stop()

        return True



    # ==================================================
    # Registration
    # ==================================================

    def register_capability(
        self,
        capability,
        handler,
    ):

        self.control_plane.pipeline.dispatcher.register(
            capability,
            handler,
        )


        return self.manager.register(
            capability,
            handler,
        )



    def register(
        self,
        capability,
        handler,
    ):

        return self.register_capability(
            capability,
            handler,
        )



    # ==================================================
    # Workflow
    # ==================================================

    def submit_workflow(
        self,
        workflow,
        context=None,
    ):


        if isinstance(
            workflow,
            str,
        ):

            workflow = type(
                "WorkflowTask",
                (),
                {

                    "capability":
                        workflow,

                    "payload":
                        context or {},

                }
            )()



        self.last_workflow = workflow


        self.control_plane.pipeline.add(
            workflow
        )


        self.workflows = (
            self.control_plane.pipeline.size()
        )


        if not self.running:

            self.start()



        return self.manager.submit(
            workflow
        )



    def execute_workflow(
        self,
        workflow=None,
    ):


        if workflow is None:

            workflow = self.last_workflow



        if workflow is None:

            return {

                "done":
                    False,

                "success":
                    False,

            }



        capability = getattr(
            workflow,
            "capability",
            None,
        )


        result = self.manager.execute(
            capability,
            workflow,
        )



        if isinstance(
            result,
            dict,
        ):

            return result



        if hasattr(
            result,
            "output",
        ):


            if isinstance(
                result.output,
                dict,
            ):

                return result.output



        return {

            "done":
                bool(result),

            "success":
                bool(result),

        }



    # ==================================================
    # Status
    # ==================================================

    def status(
        self,
    ):

        return {

            "healthy":
                True,

            "running":
                self.running,

            "workflows":
                self.workflows,

            "control_plane":
                self.control_plane.status(),

            "manager":
                self.manager.status(),

        }



    def clear(
        self,
    ):

        self.control_plane.pipeline.clear()

        self.last_workflow = None

        self.workflows = 0

        return True