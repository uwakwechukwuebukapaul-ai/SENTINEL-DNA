"""
Sentinel DNA Service Registry.

Central dependency container for
enterprise service wiring.
"""

from __future__ import annotations

from typing import Any, TypeVar, Type

T = TypeVar("T")


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

    def require(self, name: str, expected_type: Type[T] | None = None) -> T:
        """Typed dependency lookup with an actionable startup/runtime error."""
        service = self._services.get(name)
        if service is None:
            raise LookupError(f"Required service is not registered: {name}")
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(f"Service '{name}' has type {type(service).__name__}, expected {expected_type.__name__}")
        return service

    def validate_required(self, names: tuple[str, ...]) -> None:
        """Fail startup early when foundational services are missing."""
        missing = [name for name in names if self._services.get(name) is None]
        if missing:
            raise LookupError("Missing required services: " + ", ".join(missing))



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
