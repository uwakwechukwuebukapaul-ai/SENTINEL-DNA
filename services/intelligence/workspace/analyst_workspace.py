"""
Sentinel DNA Analyst Workspace.

Provides analyst-facing investigation workspace state.

Responsibilities:

- Load investigation responses
- Normalize analyst data
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
        Load normalized investigation into workspace.
        """


        investigation = (
            investigation
            or {}
        )


        risk = investigation.get(
            "risk",
            {},
        )


        if isinstance(
            risk,
            dict,
        ):

            risk_level = risk.get(
                "level",
                "unknown",
            )

            risk_score = risk.get(
                "score",
                0,
            )

        else:

            risk_level = risk

            risk_score = investigation.get(
                "risk_score",
                0,
            )


        workspace = {

            "status": (
                investigation.get(
                    "status",
                    "unknown",
                )
            ),


            "investigation_id": (
                investigation.get(
                    "investigation_id",
                )
            ),


            "case_id": (
                investigation.get(
                    "case_id",
                )
            ),


            "risk": risk_level,


            "risk_score": risk_score,


            "confidence": (
                investigation.get(
                    "confidence",
                    0.0,
                )
            ),


            "findings": (
                investigation.get(
                    "findings",
                    [],
                )
            ),


            "indicators": (
                investigation.get(
                    "indicators",
                    [],
                )
            ),


            "mitre": (
                investigation.get(
                    "mitre",
                    [],
                )
            ),


            "timeline": (
                investigation.get(
                    "timeline",
                    [],
                )
            ),


            "recommendations": (
                investigation.get(
                    "recommendations",
                    [],
                )
            ),


            "report": (
                investigation.get(
                    "report",
                    {},
                )
            ),


            "error": (
                investigation.get(
                    "error",
                )
            ),


            "loaded_at": (
                self._timestamp()
            ),

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