"""
Sentinel DNA Analyst Workspace

Provides analyst-facing investigation workspace state.

Responsibilities:
- Load investigations
- Normalize investigation data
- Provide analyst workspace payload
- Track workspace history
- Support dashboard/API consumption
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class AnalystWorkspace:
    """
    Analyst workspace manager.
    """

    def __init__(
        self,
    ) -> None:

        self.current: dict[str, Any] | None = None

        self.history: list[dict[str, Any]] = []


    # =====================================================
    # LOAD INVESTIGATION
    # =====================================================

    def load(
        self,
        investigation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Load investigation into analyst workspace.
        """

        investigation = (
            investigation
            or {}
        )


        workspace = {

            "status":
                investigation.get(
                    "status",
                    "unknown",
                ),


            "case_id":
                investigation.get(
                    "case_id",
                ),


            "risk":
                investigation.get(
                    "risk",
                    "unknown",
                ),


            "confidence":
                investigation.get(
                    "confidence",
                    0.0,
                ),


            "findings":
                investigation.get(
                    "findings",
                    [],
                ),


            "indicators":
                investigation.get(
                    "indicators",
                    [],
                ),


            "recommendations":
                investigation.get(
                    "recommendations",
                    [],
                ),


            "error":
                investigation.get(
                    "error",
                ),


            "loaded_at":
                self._timestamp(),

        }


        self.current = workspace


        self.history.append(
            workspace
        )


        return workspace



    # =====================================================
    # ACCESSORS
    # =====================================================

    def get_current(
        self,
    ) -> dict[str, Any]:

        return (
            self.current
            or {}
        )



    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history



    def clear(
        self,
    ) -> bool:

        self.current = None

        self.history.clear()

        return True



    # =====================================================
    # SERIALIZATION
    # =====================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return self.get_current()



    # =====================================================
    # INTERNAL
    # =====================================================

    @staticmethod
    def _timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()