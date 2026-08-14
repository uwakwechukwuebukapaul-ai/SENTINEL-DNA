"""
Sentinel DNA Investigation API Controller.

Application service adapter between the HTTP API
and the canonical InvestigationCoordinator.

Architecture:

HTTP API
    |
    v
InvestigationController
    |
    v
InvestigationCoordinator
    |
    v
InvestigationOrchestrator
    |
    v
RuntimeTaskExecutor
"""

from __future__ import annotations

from typing import Any

from services.intelligence.orchestration import (
    InvestigationCoordinator,
)
from services.core.serialization import serialize


class InvestigationController:
    """
    Thin API controller for investigations.

    The controller does not own investigation orchestration.

    It delegates investigation execution to the canonical
    InvestigationCoordinator supplied by the application
    service container.
    """

    def __init__(
        self,
        coordinator: InvestigationCoordinator,
    ) -> None:

        if coordinator is None:
            raise ValueError(
                "InvestigationCoordinator is required."
            )

        self.coordinator = coordinator

    def run(
        self,
        artifacts: list[dict[str, Any]],
        case_id: str | None = None,
        alert: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute an investigation through the canonical
        InvestigationCoordinator.
        """

        normalized_case_id = (
            case_id
            or (
                alert or {}
            ).get(
                "case_id"
            )
            or "UNKNOWN"
        )

        normalized_alert = dict(
            alert or {}
        )

        result = self.coordinator.investigate(
            case_id=normalized_case_id,
            alert=normalized_alert,
            artifacts=artifacts,
            **kwargs,
        )

        if result is not None:
            return serialize(result)

        return {
            "success": False,
            "status": "failed",
            "error": (
                "Invalid investigation result"
            ),
        }


__all__ = [
    "InvestigationController",
]
