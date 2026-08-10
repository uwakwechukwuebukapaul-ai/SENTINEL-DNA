"""
Sentinel DNA Investigation View

Provides analyst-facing investigation representation.

Responsibilities:
- Transform investigation intelligence into workspace format
- Prepare SOC analyst view payloads
- Preserve investigation context
- Support dashboard/API serialization
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InvestigationView:
    """
    Analyst investigation workspace view builder.
    """

    def __init__(self) -> None:

        self.history: list[dict[str, Any]] = []


    # =====================================================
    # MAIN VIEW RENDERING
    # =====================================================

    def render(
        self,
        investigation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Render analyst-ready investigation view.
        """

        investigation = (
            investigation
            or {}
        )


        view = {

            "case_id":
                investigation.get(
                    "case_id"
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


            "mitre":
                investigation.get(
                    "mitre",
                    [],
                ),


            "recommendations":
                investigation.get(
                    "recommendations",
                    [],
                ),


            "generated_at":
                self._timestamp(),

        }


        self.history.append(
            view
        )


        return view



    # =====================================================
    # SERIALIZATION
    # =====================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return latest workspace state.
        """

        if not self.history:

            return {}


        return self.history[-1]



    # =====================================================
    # HISTORY
    # =====================================================

    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return self.history



    def clear_history(
        self,
    ) -> bool:

        self.history.clear()

        return True



    # =====================================================
    # INTERNALS
    # =====================================================

    @staticmethod
    def _timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()