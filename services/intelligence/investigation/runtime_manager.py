"""
Sentinel DNA Investigation Runtime Manager

Controls investigation runtime lifecycle.
"""

from __future__ import annotations

from typing import Any

from .runtime_loader import (
    InvestigationRuntimeLoader,
)



class InvestigationRuntimeManager:
    """
    Manages investigation runtime lifecycle.
    """

    def __init__(
        self,
        loader: InvestigationRuntimeLoader | None = None,
    ) -> None:

        self.loader = (
            loader
            or InvestigationRuntimeLoader()
        )

        self.state = "initialized"



    def initialize(
        self,
    ) -> dict[str, Any]:
        """
        Initialize runtime.
        """

        self.state = "initialized"

        return self.status()



    def start(
        self,
    ) -> dict[str, Any]:
        """
        Start runtime.
        """

        runtime_status = (
            self.loader.start()
        )

        self.state = "running"

        return runtime_status



    def stop(
        self,
    ) -> dict[str, Any]:
        """
        Stop runtime.
        """

        self.loader.stop()

        self.state = "stopped"

        return self.status()



    def restart(
        self,
    ) -> dict[str, Any]:
        """
        Restart runtime.
        """

        self.stop()

        return self.start()



    def health(
        self,
    ) -> dict[str, Any]:
        """
        Runtime health check.
        """

        return {
            "state": self.state,
            "healthy": (
                self.state == "running"
            ),
        }



    def status(
        self,
    ) -> dict[str, Any]:
        """
        Return runtime status.
        """

        return {
            "state": self.state,
            "runtime": (
                self.loader.status()
            ),
        }