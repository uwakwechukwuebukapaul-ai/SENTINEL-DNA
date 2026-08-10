"""
Sentinel DNA Investigation Orchestrator.

Coordinates autonomous investigation workflow.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.investigation.context import (
    InvestigationContext,
)

from .execution_state import WorkflowState



class InvestigationOrchestrator:
    """
    Main investigation workflow coordinator.
    """


    def __init__(
        self,
        investigator=None,
        executor=None,
        reporter=None,
        decision_engine=None,
        case_manager=None,
        **kwargs,
    ) -> None:


        self.investigator = investigator

        self.executor = executor

        self.reporter = reporter

        self.decision_engine = decision_engine

        self.case_manager = case_manager

        self.state = WorkflowState()



    def investigate(
        self,
        case_id: str,
        artifacts=None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Execute complete investigation workflow.
        """

        artifacts = artifacts or []


        context = InvestigationContext(

            case_id=case_id,

            investigation_id=f"INV-{case_id}",

            artifacts=artifacts,

        )


        context.add_event(
            {
                "stage": "started",
            }
        )


        try:

            self.state.set_status(
                "running"
            )


            investigation = (
                self._run_investigator(
                    context
                )
            )


            context.set_intelligence(
                investigation
            )


            execution = (
                self._run_execution(
                    context
                )
            )


            report = (
                self._generate_report(
                    context
                )
            )


            context.set_report(
                report
            )


            context.complete()


            self.state.set_status(
                "completed"
            )


            #
            # Backward compatible response
            #
            return {

                "case_id":
                    context.case_id,


                "status":
                    context.status,


                "investigation":
                    investigation,


                "execution":
                    execution,


                "report":
                    report,


                #
                # New architecture exposure
                #
                "context":
                    context.to_dict(),

            }



        except Exception as exc:


            context.fail()


            self.state.set_status(
                "failed"
            )


            return {

                "case_id":
                    case_id,


                "status":
                    "failed",


                "error":
                    str(exc),

            }



    # =====================================================
    # INVESTIGATION ENGINE
    # =====================================================

    def _run_investigator(
        self,
        context: InvestigationContext,
    ):


        if self.investigator:


            if hasattr(
                self.investigator,
                "investigate",
            ):

                return self.investigator.investigate(
                    context.case_id,
                    context.artifacts,
                )


            if callable(
                self.investigator
            ):

                return self.investigator(
                    context.case_id,
                    context.artifacts,
                )



        return {

            "analysis":
            {

                "risk":
                    "high",

            },


            "risk":
            {

                "level":
                    "high",

                "score":
                    90,

            },


            "findings":
                [],

        }



    # =====================================================
    # EXECUTION ENGINE
    # =====================================================

    def _run_execution(
        self,
        context: InvestigationContext,
    ):


        if self.executor:


            if hasattr(
                self.executor,
                "execute",
            ):

                return self.executor.execute(
                    context.case_id,
                    context.intelligence,
                )


            if callable(
                self.executor
            ):

                return self.executor(
                    context.case_id,
                    context.intelligence,
                )



        return {

            "action":
                "contain",


            "status":
                "completed",


            "actions":
                [],

        }



    # =====================================================
    # REPORT ENGINE
    # =====================================================

    def _generate_report(
        self,
        context: InvestigationContext,
    ):


        if self.reporter:


            if hasattr(
                self.reporter,
                "generate",
            ):

                return self.reporter.generate(
                    context.case_id,
                    context.intelligence,
                )


            if callable(
                self.reporter
            ):

                return self.reporter(
                    context.case_id,
                    context.intelligence,
                )



        return {

            "case_id":
                context.case_id,


            "status":
                "completed",


            "summary":
                "Investigation completed",

        }