"""
Sentinel DNA - Runtime Service

Service facade responsible for exposing
autonomous investigation execution.

Responsibilities:

- accept investigation requests
- create runtime execution flow
- delegate to InvestigationRuntime
- normalize runtime responses
- provide stable service contract
"""

from __future__ import annotations

from typing import Any


class RuntimeService:
    """
    Public runtime service facade.
    """

    def __init__(
        self,
        runtime=None,
    ):
        """
        Dependency injection.

        runtime:
            InvestigationRuntime instance
        """

        if runtime is None:

            from services.intelligence.runtime.investigation_runtime import (
                InvestigationRuntime,
            )

            runtime = InvestigationRuntime()

        self.runtime = runtime


    def execute(
        self,
        case_id: str,
        artifacts: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute autonomous investigation.

        Returns normalized runtime result.
        """

        if artifacts is None:
            artifacts = []


        if metadata is None:
            metadata = {}


        result = self.runtime.execute(
            case_id=case_id,
            artifacts=artifacts,
            metadata=metadata,
        )


        return self._normalize_result(
            result
        )


    def investigate(
        self,
        case_id: str,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Compatibility API.

        Delegates investigation execution.
        """

        return self.execute(
            case_id=case_id,
            artifacts=artifacts,
        )


    def health(
        self,
    ) -> dict[str, Any]:
        """
        Runtime health status.
        """

        return {

            "service":
                "sentinel-dna-runtime",

            "status":
                "healthy",

        }


    def _normalize_result(
        self,
        result,
    ) -> dict[str, Any]:
        """
        Convert runtime objects into dictionaries.
        """

        if isinstance(
            result,
            dict,
        ):
            return result


        if hasattr(
            result,
            "to_dict",
        ):

            return result.to_dict()


        if hasattr(
            result,
            "__dict__",
        ):

            return vars(
                result
            )


        return {

            "status":
                "unknown",

            "result":
                result,

        }