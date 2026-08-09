"""
Sentinel DNA Agent Dispatcher

Executes autonomous investigation tasks
against registered intelligence agents.
"""

from __future__ import annotations

from typing import Any


class AgentDispatcher:
    """
    Dispatches investigation tasks to agents.
    """


    def __init__(
        self,
        agent_registry=None,
    ) -> None:

        self.agent_registry = (
            agent_registry
        )

        self.execution_history: list[
            dict[str, Any]
        ] = []


    def dispatch(
        self,
        execution_plan,
    ) -> dict[str, Any]:
        """
        Execute all tasks in plan.
        """


        results = []


        for task in execution_plan.tasks:

            result = self._execute_task(
                task
            )

            results.append(
                result
            )


        output = {

            "case_id":
                execution_plan.case_id,

            "strategy":
                execution_plan.strategy,

            "results":
                results,

            "status":
                "completed",

        }


        self.execution_history.append(
            output
        )


        return output



    def _execute_task(
        self,
        task,
    ) -> dict[str, Any]:
        """
        Execute individual agent task.
        """


        agent = (
            self._resolve_agent(
                task.agent
            )
        )


        if agent is None:

            return {

                "task_id":
                    task.task_id,

                "agent":
                    task.agent,

                "status":
                    "failed",

                "error":
                    "Agent not registered",

            }


        try:

            if hasattr(
                agent,
                "execute",
            ):

                response = agent.execute(
                    task.metadata
                )


            elif hasattr(
                agent,
                "analyze",
            ):

                response = agent.analyze(
                    task.metadata
                )


            else:

                response = {

                    "message":
                    "Agent has no execution method"

                }


            return {

                "task_id":
                    task.task_id,

                "agent":
                    task.agent,

                "status":
                    "completed",

                "result":
                    response,

            }


        except Exception as exc:

            return {

                "task_id":
                    task.task_id,

                "agent":
                    task.agent,

                "status":
                    "failed",

                "error":
                    str(exc),

            }



    def _resolve_agent(
        self,
        name: str,
    ):
        """
        Retrieve agent from registry.
        """

        if not self.agent_registry:

            return None


        if hasattr(
            self.agent_registry,
            "get",
        ):

            return self.agent_registry.get(
                name
            )


        return None



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return dispatch history.
        """

        return self.execution_history



    def clear_history(
        self,
    ) -> None:
        """
        Clear dispatch history.
        """

        self.execution_history.clear()