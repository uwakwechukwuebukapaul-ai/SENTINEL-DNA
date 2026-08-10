"""
Sentinel DNA Investigation Workflow Orchestrator.

Coordinates investigation execution from request
to analyst-ready result.
"""

from typing import Any


from ..api import (
    InvestigationAPI,
    InvestigationRequest,
)


from .models import (
    InvestigationWorkflowResult,
)



class InvestigationWorkflowOrchestrator:
    """
    Enterprise investigation workflow controller.
    """


    def __init__(self):

        self.api = (
            InvestigationAPI()
        )


    def execute(
        self,
        case_id: str,
        evidence: Any,
    ) -> InvestigationWorkflowResult:
        """
        Execute complete investigation workflow.
        """


        request = InvestigationRequest(

            case_id=case_id,

            evidence=evidence,

        )


        response = (
            self.api.investigate(
                request
            )
        )


        response_data = (
            response.to_dict()
            if hasattr(
                response,
                "to_dict",
            )
            else response
        )


        return InvestigationWorkflowResult(

            case_id=case_id,

            status="completed",

            result=response_data,

            stages=[

                "request_received",

                "investigation_execution",

                "decision_processing",

                "report_generation",

                "workflow_completed",

            ],

            metadata={

                "workflow":
                    "investigation_orchestrator",

                "engine":
                    "sentinel_dna",

            },
        )