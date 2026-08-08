"""
Sentinel DNA Investigation Execution Orchestrator

Coordinates autonomous investigation execution.

Pipeline:

Alert
 |
Investigation Context
 |
Intelligence Engines
 |
Risk Analysis
 |
Report Generation
 |
Persistence
"""

from __future__ import annotations

from typing import Any


class InvestigationExecutionOrchestrator:
    """
    Main AI investigation execution controller.
    """

    def __init__(
        self,
        investigation_repository=None,
        report_repository=None,
        engines=None,
    ) -> None:

        self.investigation_repository = (
            investigation_repository
        )

        self.report_repository = (
            report_repository
        )

        self.engines = engines or {}

        self.history: list[dict[str, Any]] = []


    def register_engine(
        self,
        name: str,
        engine: Any,
    ) -> None:
        """
        Register intelligence capability.
        """

        self.engines[name] = engine


    def execute(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute complete investigation.
        """

        investigation = None

        if self.investigation_repository:

            investigation = (
                self.investigation_repository.create(
                    case_id=case_id,
                    alert=alert,
                )
            )


        results = {}


        for name, engine in self.engines.items():

            try:

                if hasattr(
                    engine,
                    "analyze",
                ):

                    results[name] = (
                        engine.analyze(alert)
                    )

                elif hasattr(
                    engine,
                    "execute",
                ):

                    results[name] = (
                        engine.execute(alert)
                    )

            except Exception as exc:

                results[name] = {
                    "error": str(exc)
                }


        report = {

            "case_id": case_id,

            "alert": alert,

            "intelligence": results,

            "status": "completed",

        }


        if self.report_repository:

            self.report_repository.create(
                case_id=case_id,
                report=report,
            )


        execution = {

            "case_id": case_id,

            "investigation": investigation,

            "report": report,

        }


        self.history.append(
            execution
        )


        return execution


    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return executions.
        """

        return self.history