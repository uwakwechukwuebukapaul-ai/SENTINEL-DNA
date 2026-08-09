"""
Sentinel DNA Agent Registry.

Maintains available autonomous agents.
"""

from __future__ import annotations

from typing import Any



class AgentRegistry:
    """
    Registry for intelligence agents.
    """


    def __init__(self) -> None:

        self._agents: dict[str, Any] = {}



    def register(
        self,
        name: str,
        agent: Any,
    ) -> None:
        """
        Register an agent.
        """

        self._agents[name] = agent



    def get(
        self,
        name: str,
    ) -> Any:
        """
        Retrieve agent.
        """

        return self._agents.get(
            name
        )



    def list_agents(
        self,
    ) -> list[str]:

        return list(
            self._agents.keys()
        )



    def remove(
        self,
        name: str,
    ) -> None:

        self._agents.pop(
            name,
            None,
        )