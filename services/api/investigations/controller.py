"""
Investigation API Controller.

Application service layer between
HTTP routes and intelligence engine.
"""

from typing import Any
from importlib import import_module


def _load_orchestrator():
    """Load the investigation orchestrator from the available package layout."""
    module_names = (
        "...intelligence.investigation.investigation_orchestrator",
        "...intelligence.investigations.investigation_orchestrator",
        "...intelligence.investigation.orchestrator",
    )

    for module_name in module_names:
        try:
            module = import_module(module_name, package=__package__)
            return module.InvestigationOrchestrator
        except (ImportError, AttributeError):
            continue

    raise ImportError("Could not locate InvestigationOrchestrator")


InvestigationOrchestrator = _load_orchestrator()


class InvestigationController:
    """
    Executes investigations.
    """

    def __init__(
        self,
        orchestrator=None,
    ) -> None:

        self.orchestrator = (
            orchestrator
            or InvestigationOrchestrator()
        )


    def run(
        self,
        artifacts: list[dict[str, Any]],
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute investigation.
        """

        result = self.orchestrator.investigate(
            artifacts=artifacts,
            case_id=case_id,
        )

        if hasattr(
            result,
            "to_dict",
        ):
            return result.to_dict()


        if isinstance(
            result,
            dict,
        ):
            return result


        return {
            "success": False,
            "status": "failed",
            "error": "Invalid investigation result",
        }