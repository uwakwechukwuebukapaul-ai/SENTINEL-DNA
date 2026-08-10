"""
Sentinel DNA Investigation Orchestrator.

Coordinates autonomous investigation workflow.

Flow:

Case
 |
 v
Context
 |
 v
Memory
 |
 v
Investigation
 |
 v
Execution
 |
 v
Report
"""

from __future__ import annotations

from typing import Any

from services.intelligence.investigation.context import (
    InvestigationContext,
)

from services.intelligence.investigation.memory import (
    InvestigationMemory,
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

        self.memory_store: dict[str, InvestigationMemory] = {}



    def investigate(
        self,
        case_id: str,
        artifacts=None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Execute autonomous investigation workflow.
        """


        artifacts = artifacts or []


        context = InvestigationContext(

            case_id=case_id,

            investigation_id=f"INV-{case_id}",

            artifacts=artifacts,

        )


        memory = InvestigationMemory(
            investigation_id=f"INV-{case_id}"
        )


        self.memory_store[case_id] = memory



        context.add_event(
            {
                "stage":
                    "started",
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


            self._update_memory_from_investigation(
                memory,
                investigation,
            )



            execution = (
                self._run_execution(
                    context
                )
            )


            self._update_memory_from_execution(
                memory,
                execution,
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


                "context":
                    context.to_dict(),


                "memory":
                    memory.snapshot(),

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
    # INVESTIGATION
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


            "indicators":
                [],

        }



    # =====================================================
    # EXECUTION
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
    # REPORTING
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



    # =====================================================
    # MEMORY MANAGEMENT
    # =====================================================


    def _update_memory_from_investigation(
        self,
        memory: InvestigationMemory,
        investigation,
    ):


        if not isinstance(
            investigation,
            dict,
        ):

            return



        for finding in investigation.get(
            "findings",
            [],
        ):

            memory.add_finding(
                {
                    "finding":
                        finding,
                }
            )



        for indicator in investigation.get(
            "indicators",
            [],
        ):

            memory.add_indicator(
                {
                    "indicator":
                        indicator,
                }
            )



        risk = investigation.get(
            "risk"
        )


        if isinstance(
            risk,
            dict,
        ):

            score = risk.get(
                "score"
            )


            if score is not None:

                memory.add_confidence(
                    float(score) / 100
                )



    def _update_memory_from_execution(
        self,
        memory: InvestigationMemory,
        execution,
    ):


        if not isinstance(
            execution,
            dict,
        ):

            return



        for action in execution.get(
            "actions",
            [],
        ):

            memory.add_action(
                {
                    "action":
                        action,
                }
            )