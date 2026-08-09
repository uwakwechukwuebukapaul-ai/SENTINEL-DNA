"""
Sentinel DNA Action Planner.

Generates recommended SOC response actions
based on threat classification and priority.
"""

from __future__ import annotations

from typing import Any


class ActionPlanner:
    """
    Converts security findings into
    actionable response steps.
    """

    def plan(
        self,
        classification: str,
        priority: str,
    ) -> list[str]:
        """
        Generate recommended actions.
        """

        if classification == "phishing":

            return [

                "Block malicious sender and domains.",

                "Search environment for related indicators.",

                "Review affected user accounts.",

                "Reset compromised credentials if required.",

            ]


        if classification == "malware":

            return [

                "Isolate affected endpoint.",

                "Collect endpoint forensic evidence.",

                "Perform malware containment.",

                "Hunt for additional affected systems.",

            ]


        if classification == "credential_theft":

            return [

                "Disable compromised accounts.",

                "Force credential reset.",

                "Review authentication logs.",

            ]


        if priority == "P1":

            return [

                "Escalate incident immediately.",

                "Start incident response workflow.",

                "Preserve investigation evidence.",

            ]


        return [

            "Continue monitoring activity.",

            "Collect additional threat intelligence.",

            "Review analyst findings.",

        ]