"""
Investigation API Controller.

Application service layer between
HTTP routes and intelligence engine.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .schemas import InvestigationResponseSchema



def _load_orchestrator():
    """
    Dynamically load InvestigationOrchestrator.

    Supports current and future package layouts.
    """

    module_names = (
        "services.intelligence.investigation.investigation_orchestrator",
        "services.intelligence.investigations.investigation_orchestrator",
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



InvestigationOrchestrator = (
    _load_orchestrator()
)



class InvestigationController:
    """
    Executes security investigations.
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
            artifacts=artifacts,
            case_id=case_id,
        )


        serialized = (
            self._serialize_result(
                result
            )
        )


        return (
            InvestigationResponseSchema.build(
                serialized
            )
        )


    @staticmethod
    def _serialize_result(
        result: Any,
    ) -> dict[str, Any]:
        """
        Convert engine result into dictionary.
        """


        if hasattr(
            result,
            "to_dict",
        ):

            converted = result.to_dict()

            if isinstance(
                converted,
                dict,
            ):
                return converted


        if isinstance(
            result,
            dict,
        ):

            return dict(
                result
            )


        return {
            "success": False,
            "status": "failed",
            "error": (
                "Invalid investigation result"
            ),
        }