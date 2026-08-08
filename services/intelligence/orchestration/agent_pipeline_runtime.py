"""
Sentinel DNA Agent Pipeline Runtime

Bridges investigation orchestration
with task execution runtime.
"""

from .agent_pipeline import AgentPipeline


class AgentPipelineRuntime:
    """
    Runtime adapter for investigation execution.
    """


    def __init__(
        self,
        registry,
        task_executor,
    ):

        self.pipeline = AgentPipeline(
            registry=registry,
        )

        self.task_executor = task_executor



    def execute(
        self,
        plan,
        context,
    ):

        return self.pipeline.execute(
            plan,
            context,
        )