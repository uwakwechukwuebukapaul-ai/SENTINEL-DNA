"""
Sentinel DNA Investigation Registry

Central registry for investigation components.
"""

from __future__ import annotations

from typing import Any


class InvestigationRegistry:
    """
    Stores and discovers investigation components.
    """

    def __init__(self) -> None:

        self._components: dict[
            str,
            Any,
        ] = {}


    def register(
        self,
        name: str,
        component: Any,
    ) -> None:
        """
        Register investigation component.
        """

        self._components[name] = component



    def unregister(
        self,
        name: str,
    ) -> None:
        """
        Remove component.
        """

        self._components.pop(
            name,
            None,
        )



    def get(
        self,
        name: str,
    ) -> Any | None:
        """
        Retrieve component.
        """

        return self._components.get(
            name
        )



    def exists(
        self,
        name: str,
    ) -> bool:
        """
        Check component existence.
        """

        return name in self._components



    def list_components(
        self,
    ) -> list[str]:
        """
        Return registered components.
        """

        return list(
            self._components.keys()
        )



    def clear(
        self,
    ) -> None:
        """
        Remove all components.
        """

        self._components.clear()