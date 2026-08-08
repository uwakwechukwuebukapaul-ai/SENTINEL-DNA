"""
Sentinel DNA Investigation Runtime Loader

Initializes investigation runtime components.
"""

from __future__ import annotations

from typing import Any

from .investigation_registry import (
    InvestigationRegistry,
)


class InvestigationRuntimeLoader:
    """
    Loads and manages investigation runtime.
    """

    def __init__(
        self,
        registry: InvestigationRegistry | None = None,
    ) -> None:

        self.registry = (
            registry
            or InvestigationRegistry()
        )

        self.loaded = False



    def load_component(
        self,
        name: str,
        component: Any,
    ) -> None:
        """
        Register runtime component.
        """

        self.registry.register(
            name,
            component,
        )



    def load_components(
        self,
        components: dict[str, Any],
    ) -> None:
        """
        Bulk load components.
        """

        for name, component in components.items():

            self.load_component(
                name,
                component,
            )



    def start(
        self,
    ) -> dict[str, Any]:
        """
        Start investigation runtime.
        """

        self.loaded = True


        return {
            "status": "running",
            "components": (
                self.registry.list_components()
            ),
        }



    def stop(
        self,
    ) -> None:
        """
        Shutdown runtime.
        """

        self.loaded = False



    def status(
        self,
    ) -> dict[str, Any]:
        """
        Return runtime status.
        """

        return {
            "loaded": self.loaded,
            "components": (
                self.registry.list_components()
            ),
        }