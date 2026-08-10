"""
Sentinel DNA Case Repository Adapter.

Bridges dashboard services with
the investigation case management layer.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.cases.case_manager import (
    CaseManager,
)



class CaseRepositoryAdapter:
    """
    Dashboard-facing case repository.

    Converts CaseManager objects into
    dashboard-consumable dictionaries.
    """



    def __init__(
        self,
        case_manager: CaseManager | None = None,
    ) -> None:


        self.case_manager = (
            case_manager
            or CaseManager()
        )



    # =====================================================
    # GET CASE
    # =====================================================

    def get(
        self,
        case_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve case from CaseManager.
        """


        case = self.case_manager.get_case(
            case_id
        )


        if not case:

            return None



        return self._normalize(
            case
        )



    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize(
        self,
        case: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert internal case object
        into dashboard format.
        """


        timeline = case.get(
            "timeline"
        )


        evidence = case.get(
            "evidence"
        )


        return {

            "case_id": (
                case.get(
                    "case_id"
                )
            ),


            "status": (
                case.get(
                    "state",
                    "unknown",
                )
            ),


            "alert": (
                case.get(
                    "alert",
                    {},
                )
            ),


            "timeline": (
                timeline.events
                if timeline and hasattr(
                    timeline,
                    "events",
                )
                else []
            ),


            "evidence": (
                evidence.nodes
                if evidence and hasattr(
                    evidence,
                    "nodes",
                )
                else []
            ),

        }