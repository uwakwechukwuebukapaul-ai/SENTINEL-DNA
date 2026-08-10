"""
Investigation API Controller.

Application service layer between
HTTP routes and intelligence engine.

Responsible for:
- request normalization
- orchestrator execution
- result serialization
- API-safe error handling
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _load_orchestrator():
    """
    Locate InvestigationOrchestrator.

    Supports multiple package layouts
    during architecture evolution.
    """

    module_names = (
        "services.intelligence.investigation.investigation_orchestrator",
        "services.intelligence.investigations.investigation_orchestrator",
        "services.intelligence.investigation.orchestrator",
    )


    for module_name in module_names:

        try:
            module = import_module(
                module_name
            )

            return module.InvestigationOrchestrator

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
    Investigation execution service.
    """


    def __init__(
        self,
        orchestrator=None,
    ) -> None:

        self.orchestrator = (
            orchestrator
            or InvestigationOrchestrator()
        )


    # =================================================
    # EXECUTION
    # =================================================

    def run(
        self,
        artifacts: list[dict[str, Any]] | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute investigation workflow.
        """


        artifacts = (
            artifacts
            or []
        )


        try:

            result = (
                self.orchestrator.investigate(
                    artifacts=artifacts,
                    case_id=case_id,
                )
            )


            return self._serialize_result(
                result
            )


        except Exception as exc:

            return {
                "success": False,
                "status": "failed",
                "message": (
                    "Investigation execution failed."
                ),
                "error": str(exc),
                "artifacts": artifacts,
                "case_id": case_id,
            }



    # =================================================
    # SERIALIZATION
    # =================================================

    @staticmethod
    def _serialize_result(
        result: Any,
    ) -> dict[str, Any]:
        """
        Convert orchestrator output
        into API response format.
        """


        if hasattr(
            result,
            "to_dict",
        ):

            payload = result.to_dict()

            if isinstance(
                payload,
                dict,
            ):
                return payload



        if isinstance(
            result,
            dict,
        ):
            return result



        return {
            "success": False,
            "status": "failed",
            "message": (
                "Invalid investigation result."
            ),
        }