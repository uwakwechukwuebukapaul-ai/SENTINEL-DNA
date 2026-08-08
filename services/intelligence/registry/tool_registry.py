"""
Sentinel DNA Tool Registry

Manages intelligence capabilities.
"""

from __future__ import annotations

from typing import Any, Callable


class ToolRegistry:
    """
    Dynamic intelligence capability registry.
    """


    def __init__(self):

        self._tools: dict[
            str,
            Callable[..., Any],
        ] = {}



    def register(
        self,
        name: str,
        tool: Callable[..., Any],
    ) -> None:
        """
        Register intelligence capability.
        """

        self._tools[name] = tool



    def get(
        self,
        name: str,
    ) -> Callable[..., Any] | None:
        """
        Retrieve capability.
        """

        return self._tools.get(
            name
        )



    def execute(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute registered capability.
        """

        tool = self.get(name)


        if not tool:
            raise ValueError(
                f"Capability not found: {name}"
            )


        return tool(
            *args,
            **kwargs
        )



    def list_tools(
        self,
    ) -> list[str]:

        return list(
            self._tools.keys()
        )



    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._tools