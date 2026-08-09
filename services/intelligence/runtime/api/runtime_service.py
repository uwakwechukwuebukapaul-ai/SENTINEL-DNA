"""
Sentinel DNA - Runtime Service

Application service boundary for
autonomous investigation execution.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.runtime import (
    InvestigationRuntime,
    RuntimeResult,
)


class RuntimeService:
    """
    Service facade for investigation runtime.

    Responsible for:
    - runtime lifecycle
    - request validation
    - response normalization
    """


    def __init__(
        self,
        runtime: InvestigationRuntime | None = None,
    ):
        self.runtime = (
            runtime
            or InvestigationRuntime()
        )


    def start_investigation(
        self,
        case_id: str,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Execute autonomous investigation.

        Returns API-ready dictionary.
        """


        if not case_id:

            return {

                "status": "failed",

                "error":
                    "case_id is required",

            }


        result = self.runtime.execute(
            case_id=case_id,
            evidence=evidence or [],
        )


        return self._normalize_result(
            result
        )


    def get_status(
        self,
        result: RuntimeResult | dict[str, Any],
    ) -> str:
        """
        Extract execution status.
        """


        if isinstance(
            result,
            RuntimeResult,
        ):

            return result.status


        return result.get(
            "status",
            "unknown",
        )


    def _normalize_result(
        self,
        result: RuntimeResult | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert runtime output into
        stable service contract.
        """


        if isinstance(
            result,
            RuntimeResult,
        ):

            return result.to_dict()


        return result