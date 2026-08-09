"""
Sentinel DNA - Investigation Orchestrator

Coordinates investigation execution workflow.

Flow:

Case
 ↓
Investigation
 ↓
Execution
 ↓
Report
"""

from __future__ import annotations

from typing import Any

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
        **kwargs,
    ):

        self.investigator = investigator

        self.executor = executor

        self.reporter = reporter

        self.decision_engine = decision_engine

        self.state = WorkflowState()



    def investigate(
        self,
        case_id: str,
        artifacts=None,
        **kwargs,
    ):

        artifacts = artifacts or []


        try:

            investigation_result = (
                self._run_investigator(
                    case_id,
                    artifacts,
                )
            )


            execution_result = (
                self._run_execution(
                    case_id,
                    investigation_result,
                )
            )


            report_result = (
                self._generate_report(
                    case_id,
                    investigation_result,
                    execution_result,
                )
            )


            self.state.set_status(
                "completed"
            )


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

            }


        except Exception as exc:

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



    def _run_investigator(
        self,
        case_id,
        artifacts,
    ):


        if self.investigator:


            if hasattr(
                self.investigator,
                "investigate",
            ):

                return self.investigator.investigate(
                    case_id,
                    artifacts,
                )


            if callable(
                self.investigator
            ):

                return self.investigator(
                    case_id,
                    artifacts,
                )


        return {

            "analysis":
            {

                "risk":
                    "high",

                "threat":
                    "credential_phishing",

            }

        }



    def _run_execution(
        self,
        case_id,
        investigation,
    ):


        if self.executor:


            if hasattr(
                self.executor,
                "execute",
            ):

                return self.executor.execute(
                    case_id,
                    investigation,
                )


            if callable(
                self.executor
            ):

                return self.executor(
                    case_id,
                    investigation,
                )


        return {

            "action":
                "contain",

            "status":
                "completed",

        }



    def _generate_report(
        self,
        case_id,
        investigation,
        execution,
    ):


        if self.reporter:


            if hasattr(
                self.reporter,
                "generate",
            ):

                return self.reporter.generate(
                    case_id,
                    investigation,
                    execution,
                )


            if callable(
                self.reporter
            ):

                return self.reporter(
                    case_id,
                    investigation,
                    execution,
                )


        return {

            "status":
                "completed",

            "case_id":
                case_id,

        }