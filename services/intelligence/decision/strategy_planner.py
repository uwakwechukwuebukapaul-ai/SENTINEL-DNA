"""
Sentinel DNA Investigation Strategy Planner

Converts AI decisions into investigation workflows.
"""

from __future__ import annotations

from typing import Any


class StrategyPlanner:
    """
    Creates investigation execution plans.
    """


    def plan(
        self,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate investigation strategy.
        """


        action = decision.get(
            "decision",
            "monitor",
        )


        severity = decision.get(
            "severity",
            "",
        )


        if action == "respond":

            strategy = "incident_response"

            steps = [
                "collect_evidence",
                "analyze_iocs",
                "map_attack",
                "recommend_containment",
            ]


        elif action == "respond_immediately":

            strategy = "rapid_containment"

            steps = [
                "collect_evidence",
                "identify_scope",
                "analyze_threat",
                "contain_activity",
            ]


        elif action == "investigate_further":

            strategy = "deep_investigation"

            steps = [
                "collect_context",
                "enrich_intelligence",
                "perform_hunting",
            ]


        else:

            strategy = "monitoring"

            steps = [
                "observe_activity",
                "collect_future_events",
            ]


        return {

            "strategy": strategy,

            "severity": severity,

            "steps": steps,

        }