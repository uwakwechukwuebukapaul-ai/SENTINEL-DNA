"""
Sentinel DNA Investigation API Controller.

Application-facing API boundary for
autonomous investigations.
"""

from typing import Any

from ..service import (
    UnifiedInvestigationService,
)

from .models import (
    InvestigationRequest,
    InvestigationResponse,
)



class InvestigationAPI:
    """
    Investigation API facade.

    Keeps external callers isolated from
    internal intelligence architecture.
    """


    def __init__(self):

        self.service = (
            UnifiedInvestigationService()
        )


    def investigate(
        self,
        request: InvestigationRequest | dict[str, Any],
    ) -> InvestigationResponse:
        """
        Execute investigation request.
        """


        if isinstance(
            request,
            dict,
        ):

            request = InvestigationRequest(
                case_id=request.get(
                    "case_id",
                    "UNKNOWN",
                ),

                evidence=request.get(
                    "evidence",
                    {},
                ),

                metadata=request.get(
                    "metadata",
                    {},
                ),
            )


        result = (
            self.service.investigate(
                case_id=request.case_id,
                evidence=request.evidence,
            )
        )


        result_data = (
            result.to_dict()
            if hasattr(
                result,
                "to_dict",
            )
            else result
        )


        return InvestigationResponse(

            case_id=request.case_id,

            status="completed",

            result=result_data,

            metadata={

                "api":
                    "investigation_api",

                "service":
                    "unified_investigation_service",

            },
        )