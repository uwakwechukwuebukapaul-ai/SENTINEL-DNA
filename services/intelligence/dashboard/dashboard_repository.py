"""
Sentinel DNA Dashboard Repository.

Retrieves investigation data from
case intelligence services.
"""

from __future__ import annotations

from typing import Any


class DashboardRepository:
    """
    Dashboard data access layer.
    """


    def __init__(
        self,
        case_repository=None,
        fallback_provider=None,
    ) -> None:

        self.case_repository = case_repository

        self.fallback_provider = fallback_provider



    def get_investigation(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve investigation data.
        """


        if self.case_repository:

            case = self.case_repository.get_case(
                case_id
            )

            if case:

                return self._normalize_case(
                    case
                )


        if self.fallback_provider:

            return self.fallback_provider.get(
                case_id
            )


        return {

            "case_id": case_id,

            "status": "unknown",

            "risk": {
                "level": "unknown",
                "score": 0,
            },

            "confidence": 0,

            "findings": [],

            "indicators": [],

            "mitre": [],

            "timeline": [],

            "recommendations": [],

            "report": {},

        }



    def _normalize_case(
        self,
        case: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert CaseManager object
        into dashboard contract.
        """


        return {

            "case_id":
                case.get(
                    "case_id"
                ),


            "investigation_id":
                case.get(
                    "investigation_id"
                ),


            "status":
                case.get(
                    "state",
                    "unknown",
                ),


            "risk":
                case.get(
                    "risk",
                    {
                        "level": "unknown",
                        "score": 0,
                    },
                ),


            "confidence":
                case.get(
                    "confidence",
                    0,
                ),


            "findings":
                case.get(
                    "findings",
                    [],
                ),


            "indicators":
                case.get(
                    "indicators",
                    [],
                ),


            "mitre":
                case.get(
                    "mitre",
                    [],
                ),


            "timeline":
                case.get(
                    "timeline",
                    [],
                ),


            "recommendations":
                case.get(
                    "recommendations",
                    [],
                ),


            "report":
                case.get(
                    "report",
                    {},
                ),

        }