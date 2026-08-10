"""
Sentinel DNA Investigation API Controller.

Application service layer between
HTTP routes and the canonical investigation
orchestration engine.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.orchestration import (
    InvestigationOrchestrator,
)


class InvestigationController:
    """
    API controller for investigations.

    Uses the canonical Sentinel DNA investigation
    orchestration layer rather than dynamically
    discovering legacy orchestrator implementations.
    """

    def __init__(
        self,
        orchestrator: InvestigationOrchestrator | None = None,
    ) -> None:
        self.orchestrator = (
            orchestrator
            if orchestrator is not None
            else InvestigationOrchestrator()
        )

    def run(
        self,
        artifacts: list[dict[str, Any]],
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an investigation workflow.
        """

        result = self.orchestrator.investigate(
            case_id=case_id or "UNKNOWN",
            artifacts=artifacts,
        )

        if hasattr(result, "to_dict"):
            return result.to_dict()

        if isinstance(result, dict):
            return result

        return {
            "success": False,
            "status": "failed",
            "error": "Invalid investigation result",
        }
