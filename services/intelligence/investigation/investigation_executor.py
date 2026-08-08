"""
Sentinel DNA Investigation Executor

Executes investigation plans.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from .agent_dispatcher import (
    InvestigationAgentDispatcher,
)



class InvestigationExecutor:
    """
    Executes investigation workflows.

    Converts investigation plans into
    agent executions.
    """


    def __init__(
        self,
        dispatcher: InvestigationAgentDispatcher | None = None,
    ) -> None:

        self.dispatcher = (
            dispatcher
            or InvestigationAgentDispatcher()
        )

        self.history: list[
            dict[str, Any]
        ] = []



    def execute(
        self,
        plan: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute investigation plan.
        """

        started = datetime.now(
            UTC
        )


        findings = []

        errors = []


        for task in plan.get(
            "tasks",
            [],
        ):

            try:

                result = (
                    self.dispatcher.dispatch(
                        task["name"],
                        context,
                    )
                )

                findings.append(
                    result
                )


            except Exception as exc:

                errors.append(
                    {
                        "task": task.get(
                            "name"
                        ),
                        "error": str(exc),
                    }
                )


        completed = datetime.now(
            UTC
        )


        execution = {

            "case_id": plan.get(
                "case_id"
            ),

            "status": (
                "completed"
                if not errors
                else "partial"
            ),

            "findings": findings,

            "errors": errors,

            "duration_seconds": (
                completed - started
            ).total_seconds(),

        }


        self.history.append(
            execution
        )


        return execution



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return execution history.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:
        """
        Clear execution history.
        """

        self.history.clear()