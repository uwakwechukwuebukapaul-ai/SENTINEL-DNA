"""
Sentinel DNA Investigation Agent Registry

Manages intelligence agents.
"""

from __future__ import annotations

from typing import Any, Callable



class InvestigationAgentRegistry:
    """
    Registry for investigation agents.
    """

    def __init__(self) -> None:

        self.agents: dict[
            str,
            dict[str, Any],
        ] = {}



    def register(
        self,
        name: str,
        capability: str,
        handler: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Register an agent.
        """

        agent = {
            "name": name,
            "capability": capability,
            "handler": handler,
            "status": "active",
        }


        self.agents[name] = agent


        return agent



    def get(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve agent.
        """

        return self.agents.get(
            name
        )



    def list_agents(
        self,
    ) -> list[dict[str, Any]]:
        """
        List registered agents.
        """

        return list(
            self.agents.values()
        )



    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.agents