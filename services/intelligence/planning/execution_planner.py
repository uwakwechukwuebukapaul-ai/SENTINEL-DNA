"""
Sentinel DNA Execution Planner

Transforms investigation strategy
into executable agent tasks.
"""

from __future__ import annotations

from typing import Any

from .execution_plan import (
    ExecutionPlan,
    InvestigationTask,
)


class ExecutionPlanner:
    """
    Creates autonomous investigation plans.
    """


    def __init__(
        self,
    ) -> None:

        self.counter = 0


    def create_plan(
        self,
        case_id: str,
        strategy: dict[str, Any],
        agents: list[str],
    ) -> ExecutionPlan:
        """
        Build execution workflow.
        """


        plan = ExecutionPlan(

            case_id=case_id,

            strategy=strategy.get(
                "strategy",
                "unknown",
            ),

        )


        for agent in agents:

            self.counter += 1


            task = InvestigationTask(

                task_id=(
                    f"TASK-{self.counter:04d}"
                ),

                agent=agent,

                action=self._resolve_action(
                    agent
                ),

                priority=(
                    "high"
                    if strategy.get(
                        "strategy"
                    )
                    in [
                        "incident_response",
                        "rapid_containment",
                    ]
                    else "normal"
                ),

            )


            plan.add_task(
                task
            )


        return plan



    def _resolve_action(
        self,
        agent: str,
    ) -> str:
        """
        Map agent to action.
        """

        actions = {

            "email_analysis_agent":
                "analyze_email_evidence",

            "ioc_enrichment_agent":
                "enrich_indicators",

            "threat_intelligence_agent":
                "collect_threat_intelligence",

            "malware_analysis_agent":
                "analyze_malware",

            "sandbox_agent":
                "execute_sandbox_analysis",

            "threat_hunting_agent":
                "hunt_environment",

        }


        return actions.get(
            agent,
            "perform_investigation",
        )