"""
Sentinel DNA - Runtime Integration Adapter

Responsible for connecting external
investigation requests with the runtime
execution layer.

Responsibilities:

- normalize investigation payloads
- invoke RuntimeService
- enrich runtime responses
- maintain integration contracts
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class RuntimeAdapter:
    """
    Enterprise runtime integration boundary.
    """

    def __init__(
        self,
        runtime_service=None,
    ):
        """
        Dependency injection.

        runtime_service:
            RuntimeService instance
        """

        if runtime_service is None:

            from services.intelligence.runtime.api.runtime_service import (
                RuntimeService,
            )

            runtime_service = RuntimeService()

        self.runtime_service = runtime_service


    def execute(
        self,
        investigation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute investigation through runtime.

        Input example:

        {
            "case_id": "CASE-001",
            "severity": "high",
            "artifacts": []
        }
        """

        normalized = self._normalize(
            investigation
        )


        case_id = normalized.get(
            "case_id",
            "CASE-UNKNOWN",
        )


        artifacts = normalized.get(
            "artifacts",
            [],
        )


        result = self.runtime_service.execute(
            case_id=case_id,
            artifacts=artifacts,
            metadata=normalized,
        )


        return self._build_response(
            case_id,
            result,
        )


    def investigate(
        self,
        case_id: str,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Compatibility interface.
        """

        return self.execute(
            {
                "case_id": case_id,
                "artifacts": artifacts or [],
            }
        )


    def health(
        self,
    ) -> dict[str, Any]:
        """
        Integration health check.
        """

        return {

            "adapter":
                "runtime-adapter",

            "status":
                "healthy",

        }


    def _normalize(
        self,
        investigation,
    ) -> dict[str, Any]:
        """
        Normalize incoming objects.
        """

        if investigation is None:
            return {}


        if isinstance(
            investigation,
            dict,
        ):
            return investigation


        if hasattr(
            investigation,
            "to_dict",
        ):
            return investigation.to_dict()


        if hasattr(
            investigation,
            "__dict__",
        ):
            return vars(
                investigation
            )


        return {}


    def _build_response(
        self,
        case_id: str,
        result,
    ) -> dict[str, Any]:
        """
        Create stable integration response.
        """

        if hasattr(
            result,
            "to_dict",
        ):

            result = result.to_dict()


        return {

            "case_id":
                case_id,

            "status":
                result.get(
                    "status",
                    "completed",
                )
                if isinstance(
                    result,
                    dict,
                )
                else "completed",


            "runtime":
                result,


            "metadata": {

                "engine":
                    "sentinel-dna-runtime",

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

            },

        }