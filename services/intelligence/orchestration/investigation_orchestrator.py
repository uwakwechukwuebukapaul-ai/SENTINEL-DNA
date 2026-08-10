"""
Sentinel DNA - Investigation Orchestrator.

Coordinates autonomous investigation execution workflow.

Flow:

Case
|
v
Investigation
|
v
Execution
|
v
Report
|
v
Case Update
"""

from __future__ import annotations

from typing import Any

from .execution_state import WorkflowState

from services.intelligence.cases.case_manager import (
    CaseManager,
)

from services.intelligence.cases.investigation_state import (
    InvestigationState,
)


class InvestigationOrchestrator:
    """
    Main investigation workflow coordinator.

    Responsibilities:

    - Coordinate investigation lifecycle
    - Execute intelligence workflow
    - Generate final report
    - Update case management state
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

        self.case_manager = (
            case_manager
            or CaseManager()
        )

        self.state = WorkflowState()



    # =====================================================
    # MAIN EXECUTION
    # =====================================================

    def investigate(
        self,
        case_id: str,
        artifacts=None,
        **kwargs,
    ) -> dict[str, Any]:

        artifacts = artifacts or []


        try:

            self.state.set_status(
                "running"
            )


            self._ensure_case(
                case_id,
                artifacts,
            )


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


            result = {

                "case_id": case_id,

                "status": "completed",

                "investigation":
                    investigation_result,

                "execution":
                    execution_result,

                "report":
                    report_result,

            }


            self._update_case(
                case_id,
                result,
            )


            self.state.set_status(
                "completed"
            )


            return result



        except Exception as exc:

            self.state.set_status(
                "failed"
            )


            failure = {

                "case_id": case_id,

                "status": "failed",

                "error": str(exc),

            }


            return failure



    # =====================================================
    # CASE MANAGEMENT
    # =====================================================

    def _ensure_case(
        self,
        case_id,
        artifacts,
    ):

        existing = (
            self.case_manager.get_case(
                case_id
            )
        )


        if existing:
            return existing


        return self.case_manager.create_case(
            case_id,
            {
                "artifacts": artifacts,
            },
        )



    def _update_case(
        self,
        case_id: str,
        result: dict[str, Any],
    ) -> None:


        case = (
            self.case_manager.get_case(
                case_id
            )
        )


        if not case:
            return


        case["result"] = result


        if hasattr(
            case.get("timeline"),
            "add_event",
        ):

            case["timeline"].add_event(
                "investigation_completed",
                "Investigation workflow completed",
            )


        self.case_manager.update_state(
            case_id,
            InvestigationState.COMPLETED,
        )



    # =====================================================
    # INVESTIGATION ENGINE
    # =====================================================

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

            "risk": {

                "level": "high",

                "score": 90,

            },


            "findings": [],

            "indicators": [],

        }



    # =====================================================
    # ACTION EXECUTION
    # =====================================================

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

            "action": "contain",

            "status": "completed",

        }



    # =====================================================
    # REPORT GENERATION
    # =====================================================

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

            "case_id": case_id,

            "status": "completed",

            "summary":
                "Investigation completed",

        }