"""
Investigation API Controller.

Application service layer between
HTTP routes and intelligence engine.
"""

from __future__ import annotations

from typing import Any
from importlib import import_module


def _load_orchestrator():
    """
    Locate investigation orchestrator.
    """

    module_names = (
        "services.intelligence.investigation.investigation_orchestrator",
        "services.intelligence.investigation.orchestrator",
        "services.intelligence.orchestration.investigation_orchestrator",
    )


    for module_name in module_names:

        try:

            module = import_module(
                module_name
            )

            return (
                module.InvestigationOrchestrator
            )


        except (
            ImportError,
            AttributeError,
        ):

            continue


    raise ImportError(
        "Could not locate InvestigationOrchestrator"
    )



InvestigationOrchestrator = _load_orchestrator()



class InvestigationController:
    """
    API controller for investigations.
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
        Execute investigation workflow.
        """


        result = self.orchestrator.investigate(
            case_id=case_id or "UNKNOWN",
            artifacts=artifacts,
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

            "error":
                "Invalid investigation result",

        }