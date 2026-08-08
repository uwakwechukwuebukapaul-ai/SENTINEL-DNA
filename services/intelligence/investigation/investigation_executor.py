"""
Sentinel DNA Investigation Executor

Executes investigation plans.
"""

from __future__ import annotations

from typing import Any

from .agent_dispatcher import (
    InvestigationAgentDispatcher,
)



class InvestigationExecutor:
    """
    Executes investigation workflows.
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

        findings = []


        for task in plan.get(
            "tasks",
            [],
        ):

            result = (
                self.dispatcher.dispatch(
                    task["name"],
                    context,
                )
            )

            findings.append(
                result
            )


        execution = {
            "case_id": plan.get(
                "case_id"
            ),
            "status": "completed",
            "findings": findings,
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