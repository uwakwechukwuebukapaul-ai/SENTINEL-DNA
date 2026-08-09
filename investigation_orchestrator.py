"""
Sentinel DNA Investigation Orchestrator
"""

from .execution_state import WorkflowState
from .investigation_plan import InvestigationPlan



class InvestigationOrchestrator:



    def __init__(
        self,
        investigator=None,
        executor=None,
        reporter=None,
        **kwargs,
    ):


        self.investigator = investigator

        self.executor = executor

        self.reporter = reporter

        self.state = WorkflowState()



    def create_plan(
        self,
        case_id,
        alert=None,
    ):


        return InvestigationPlan(

            case_id=case_id,

            name=(
                "Standard Security Investigation"
            ),

            plan_name=(
                "Standard Security Investigation"
            ),

            agents=[

                "investigation_execution",

                "threat_intelligence",

                "ioc_enrichment",

            ],

        )



    def investigate(
        self,
        case_id,
        artifacts=None,
        alert=None,
    ):


        artifacts = (
            artifacts
            or alert
            or []
        )


        try:


            if self.investigator:


                try:

                    investigation = (
                        self.investigator.investigate(
                            case_id,
                            artifacts,
                        )
                    )

                except TypeError:

                    investigation = (
                        self.investigator.investigate(
                            case_id=case_id,
                            artifacts=artifacts,
                        )
                    )


            else:


                investigation = {

                    "analysis": {

                        "risk":
                            "high"

                    }

                }



            if self.executor:


                execution = (
                    self.executor.execute(
                        investigation
                    )
                )


            else:


                execution = {

                    "action":
                        "contain"

                }



            if self.reporter:


                report = (
                    self.reporter.generate(
                        investigation,
                        execution,
                    )
                )


            else:


                report = {

                    "status":
                        "completed"

                }



            self.state.complete()



            return {

                "case_id":
                    case_id,

                "status":
                    "completed",

                "investigation":
                    investigation,

                "execution":
                    execution,

                "report":
                    report,

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

            }