"""
Sentinel DNA Response Orchestrator.

Coordinates:

- action planning
- approval checks
- execution
- audit generation
"""

from __future__ import annotations

from typing import Any

from .action_planner import ActionPlanner
from .execution_engine import ExecutionEngine
from .approval_manager import ApprovalManager



class ResponseOrchestrator:
    """
    Enterprise response workflow coordinator.
    """

    def __init__(
        self,
        action_planner=None,
        execution_engine=None,
        approval_manager=None,
    ) -> None:


        self.action_planner = (
            action_planner
            or ActionPlanner()
        )


        self.execution_engine = (
            execution_engine
            or ExecutionEngine()
        )


        self.approval_manager = (
            approval_manager
            or ApprovalManager()
        )


        self.history: list[
            dict[str, Any]
        ] = []



    def orchestrate(
        self,
        intelligence: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute response workflow.
        """

        actions = self.action_planner.plan(
            intelligence
        )


        approval_required = (
            self.approval_manager
            .requires_approval(
                actions
            )
        )


        executed_actions = []


        if not approval_required:

            executed_actions = (
                self.execution_engine.execute(
                    actions
                )
            )


        result = {

            "status":
                "completed",


            "actions":
                executed_actions
                if executed_actions
                else actions,


            "approval_required":
                approval_required,


            "audit":
                {
                    "engine":
                        "sentinel-dna-response-orchestrator",
                },
        }


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        return self.history.copy()



    def clear_history(
        self,
    ) -> None:
        self.history.clear()