"""
Sentinel DNA Agent Orchestrator.

Coordinates autonomous agent execution.
"""

from __future__ import annotations

from typing import Any



class AgentOrchestrator:
    """
    Executes registered intelligence agents.
    """


    def __init__(
        self,
        registry,
    ) -> None:

        self.registry = registry

        self.history: list[dict[str, Any]] = []



    def execute(
        self,
        agent_name: str,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute an autonomous agent.
        """


        agent = (
            self.registry.get(
                agent_name
            )
        )


        if agent is None:

            return {

                "status":
                    "failed",

                "error":
                    "agent_not_found",

            }



        result = (
            agent.investigate(
                investigation
            )
        )


        execution = {

            "agent":
                agent_name,


            "status":
                result.get(
                    "status",
                    "completed",
                ),


            "result":
                result,

        }


        self.history.append(
            execution
        )


        return execution



    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history.copy()



    def clear_history(
        self,
    ) -> None:

        self.history.clear()