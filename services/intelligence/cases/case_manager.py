"""
Sentinel DNA Case Manager

Enterprise investigation case lifecycle.
"""

from __future__ import annotations

from typing import Any

from .case_timeline import (
    CaseTimeline,
)

from .evidence_graph import (
    EvidenceGraph,
)

from .investigation_state import (
    InvestigationState,
)


class CaseManager:
    """
    Enterprise case lifecycle manager.
    """


    def __init__(
        self,
    ) -> None:

        self.cases: dict[str, dict[str, Any]] = {}



    # =====================================================
    # CREATE CASE
    # =====================================================

    def create_case(
        self,
        case_id: str,
        alert: dict[str, Any],
    ):

        case = {

            "case_id": case_id,

            "alert": alert,

            "state":
                InvestigationState.CREATED.value,

            "timeline":
                CaseTimeline(),

            "evidence":
                EvidenceGraph(),

        }


        self.cases[case_id] = case


        case["timeline"].add_event(
            "case_created",
            "Investigation case created",
        )


        return case



    # =====================================================
    # GET CASE
    # =====================================================

    def get_case(
        self,
        case_id: str,
    ):

        return self.cases.get(
            case_id
        )



    # =====================================================
    # UPDATE STATE
    # =====================================================

    def update_state(
        self,
        case_id: str,
        state: InvestigationState,
    ):

        case = self.cases.get(
            case_id
        )


        if not case:

            raise ValueError(
                "Case not found"
            )


        case["state"] = state.value


        case["timeline"].add_event(
            "state_changed",
            f"Case moved to {state.value}",
        )


        return case



    # =====================================================
    # ATTACH INVESTIGATION RESULT
    # =====================================================

    def update_investigation_result(
        self,
        case_id: str,
        result: dict[str, Any],
    ):
        """
        Attach intelligence output
        to an existing investigation case.
        """


        case = self.cases.get(
            case_id
        )


        if not case:

            raise ValueError(
                "Case not found"
            )


        case["investigation_id"] = (
            result.get(
                "investigation_id"
            )
        )


        case["risk"] = (
            result.get(
                "risk",
                {
                    "level": "unknown",
                    "score": 0,
                },
            )
        )


        case["confidence"] = (
            result.get(
                "confidence",
                0.0,
            )
        )


        case["findings"] = (
            result.get(
                "findings",
                [],
            )
        )


        case["indicators"] = (
            result.get(
                "indicators",
                [],
            )
        )


        case["mitre"] = (
            result.get(
                "mitre",
                [],
            )
        )


        case["timeline_data"] = (
            result.get(
                "timeline",
                [],
            )
        )


        case["recommendations"] = (
            result.get(
                "recommendations",
                [],
            )
        )


        case["report"] = (
            result.get(
                "report",
                {},
            )
        )


        case["timeline"].add_event(
            "investigation_completed",
            "Investigation results attached",
        )


        return case