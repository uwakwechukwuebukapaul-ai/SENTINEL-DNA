"""
Sentinel DNA Agent Pipeline

Executes investigation agents
through the orchestration layer.
"""

from __future__ import annotations

from .orchestration_result import (
    OrchestrationResult,
)


class AgentPipeline:
    """
    Executes agents defined in an investigation plan.
    """


    def __init__(
        self,
        registry,
    ) -> None:

        self.registry = registry



    def execute(
        self,
        plan,
        context,
    ) -> OrchestrationResult:
        """
        Execute pipeline agents.
        """

        result = OrchestrationResult(
            plan_name=plan.name
            if hasattr(plan, "name")
            else getattr(
                plan,
                "plan_name",
                "Unknown",
            ),

            success=True,
        )


        for agent_name in plan.agents:

            agent = self.registry.get(
                agent_name
            )


            if agent is None:

                result.add_error(
                    f"Agent not found: {agent_name}"
                )

                result.success = False

                continue



            try:

                agent_result = agent.execute(
                    context
                )


                result.add_agent_result(
                    agent_name,
                    agent_result,
                )


                # IMPORTANT:
                # Track successful execution

                result.agents_executed.append(
                    agent_name
                )


            except Exception as exc:

                result.add_error(
                    f"{agent_name} execution failed: {exc}"
                )

                result.success = False



        return result