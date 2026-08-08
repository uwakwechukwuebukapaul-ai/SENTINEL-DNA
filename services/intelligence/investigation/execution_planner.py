"""
Sentinel DNA Investigation Execution Planner

Creates investigation execution plans.
"""

from __future__ import annotations

from typing import Any



class InvestigationExecutionPlanner:
    """
    Generates investigation task plans.
    """

    def __init__(self) -> None:

        self.history: list[
            dict[str, Any]
        ] = []



    def create_plan(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create investigation execution plan.
        """

        severity = alert.get(
            "severity",
            "medium",
        )


        tasks = [
            {
                "name": "evidence_collection",
                "priority": 1,
            },
            {
                "name": "ioc_analysis",
                "priority": 2,
            },
            {
                "name": "mitre_mapping",
                "priority": 3,
            },
            {
                "name": "risk_assessment",
                "priority": 4,
            },
        ]


        if severity == "critical":

            tasks.insert(
                0,
                {
                    "name": "urgent_triage",
                    "priority": 0,
                },
            )


        plan = {
            "case_id": case_id,
            "severity": severity,
            "tasks": tasks,
            "status": "created",
        }


        self.history.append(
            plan
        )


        return plan



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return planning history.
        """

        return self.history



    def clear_history(
        self,
    ) -> None:
        """
        Clear planning history.
        """

        self.history.clear()