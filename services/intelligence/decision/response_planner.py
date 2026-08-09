"""
SOC Response Planner

Generates recommended analyst actions.
"""


class ResponsePlanner:
    """
    Creates response recommendations.
    """

    def generate(
        self,
        risk,
    ) -> list[str]:
        """
        Generate recommended actions.
        """

        if risk.severity == "critical":

            return [
                "Isolate affected assets",
                "Block malicious indicators",
                "Collect forensic evidence",
                "Escalate incident",
            ]


        if risk.severity == "high":

            return [
                "Investigate indicators",
                "Review affected accounts",
                "Monitor activity",
            ]


        return [
            "Continue monitoring",
            "Record investigation outcome",
        ]