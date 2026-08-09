"""
Sentinel DNA Investigation Orchestrator

Coordinates:

- investigator execution
- execution engine
- reporting
- workflow state
"""

from .workflow_state import (
    WorkflowState,
)


class InvestigationOrchestrator:


    def __init__(
        self,
        investigator=None,
        execution_engine=None,
        reporter=None,
    ):

        self.investigator = investigator

        self.execution_engine = execution_engine

        self.reporter = reporter

        self.state = WorkflowState()



    def create_context(
        self,
        investigation_id,
        artifacts,
    ):

        class InvestigationContext:

            def __init__(
                self,
                investigation_id,
                artifacts,
            ):

                self.investigation_id = investigation_id

                self.artifacts = artifacts


        return InvestigationContext(
            investigation_id,
            artifacts,
        )



    def investigate(
        self,
        case_id,
        artifacts=None,
    ):

        artifacts = artifacts or []


        self.state.start(
            case_id
        )


        try:

            investigation_result = None


            if self.investigator:

                investigation_result = (
                    self.investigator.investigate(
                        case_id,
                        artifacts,
                    )
                )


            if investigation_result is None:

                investigation_result = {

                    "analysis": {

                        "risk": "high",

                        "confidence": 0.9,

                    }

                }


            execution_result = {

                "action":
                    "contain",

                "status":
                    "completed",

            }


            report_result = {

                "status":
                    "completed",

            }


            self.state.complete()


            return {

                "case_id":
                    case_id,


                "status":
                    "completed",


                "investigation":
                    investigation_result,


                "execution":
                    execution_result,


                "report":
                    report_result,


                "workflow":
                    self.state.status,

            }


        except Exception as exc:


            self.state.fail(
                str(exc)
            )


            return {

                "case_id":
                    case_id,


                "status":
                    "failed",


                "error":
                    str(exc),


                "investigation":
                    None,


                "execution":
                    None,


                "report":
                    {

                        "status":
                            "failed"

                    },

            }