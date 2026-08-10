"""
Sentinel DNA Service Registry.

Central dependency container for
enterprise service wiring.
"""

from __future__ import annotations

from typing import Any


class ServiceRegistry:
    """
    Application dependency container.
    """


    def __init__(self):

        self._services: dict[str, Any] = {}



    def register(
        self,
        name: str,
        service: Any,
    ) -> None:
        """
        Register service instance.
        """

        self._services[name] = service



    def get(
        self,
        name: str,
    ) -> Any:
        """
        Retrieve service.
        """

        return self._services.get(
            name
        )



    def has(
        self,
        name: str,
    ) -> bool:

        return name in self._services



    def clear(
        self,
    ) -> None:

        self._services.clear()



    def all(
        self,
    ) -> dict[str, Any]:

        return self._services.copy()