"""
Sentinel DNA Action Planner.

Converts recommendation intelligence
into executable response actions.
"""

from __future__ import annotations

from typing import Any


class ActionPlanner:
    """
    Creates response execution plans.
    """

    def plan(
        self,
        intelligence: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build action plan.
        """

        candidates = intelligence.get(
            "automation_candidates",
            [],
        )

        actions = []


        for candidate in candidates:

            actions.append(
                {
                    "name": candidate,

                    "status":
                        "planned",

                    "risk":
                        self._risk_level(
                            candidate
                        ),
                }
            )


        return actions



    def _risk_level(
        self,
        action: str,
    ) -> str:

        action = action.lower()


        if (
            "isolation" in action
            or "blocking" in action
        ):

            return "medium"


        return "low"