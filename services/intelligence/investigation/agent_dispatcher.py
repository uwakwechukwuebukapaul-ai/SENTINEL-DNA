"""
Sentinel DNA Investigation Agent Dispatcher

Routes investigation tasks to intelligence agents.
"""

from __future__ import annotations

from typing import Any, Callable


class InvestigationAgentDispatcher:
    """
    Dispatches investigation tasks.
    """

    def __init__(self) -> None:

        self.agents: dict[
            str,
            Callable[..., dict[str, Any]]
        ] = {}

        self.history: list[
            dict[str, Any]
        ] = []


    def register_agent(
        self,
        name: str,
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        """
        Register investigation agent.
        """

        self.agents[name] = handler



    def dispatch(
        self,
        task_name: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute matching agent.
        """

        if task_name not in self.agents:

            result = {
                "task": task_name,
                "status": "failed",
                "error": "Agent not found",
            }

            self.history.append(result)

            return result


        result = self.agents[task_name](
            context
        )


        execution = {
            "task": task_name,
            "status": "completed",
            "result": result,
        }


        self.history.append(
            execution
        )


        return execution



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return dispatch history.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:
        """
        Clear history.
        """

        self.history.clear()