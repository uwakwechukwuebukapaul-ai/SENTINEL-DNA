"""
Sentinel DNA Approval Manager.

Controls human-in-the-loop response decisions.
"""

from __future__ import annotations

from typing import Any


class ApprovalManager:
    """
    Determines whether approval is required.
    """

    def requires_approval(
        self,
        actions: list[dict[str, Any]],
    ) -> bool:
        """
        High-impact actions require approval.
        """

        for action in actions:

            risk = action.get(
                "risk",
                "low",
            )

            if risk == "medium":

                return True


        return False