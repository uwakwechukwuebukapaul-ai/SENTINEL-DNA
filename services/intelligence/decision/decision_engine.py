"""
Sentinel DNA Decision Intelligence Engine
"""

from datetime import datetime, timezone
from typing import Any


class DecisionEngine:
    """
    Converts intelligence findings into
    SOC response decisions.
    """


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        self.history: list[dict[str, Any]] = []



    def decide(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        if investigation is None:
            investigation = {}


        case_id = investigation.get(
            "case_id",
            "UNKNOWN",
        )


        indicators = investigation.get(
            "indicators",
            [],
        )


        confidence = investigation.get(
            "confidence",
            0.0,
        )


        indicator_count = len(
            indicators
        )


        if indicator_count >= 3 and confidence >= 0.8:

            severity = "critical"
            priority = "immediate"

            actions = [
                "Isolate affected assets",
                "Collect forensic evidence",
                "Block malicious indicators",
            ]


        elif indicator_count > 0:

            severity = "high"
            priority = "high"

            actions = [
                "Investigate indicators",
                "Review affected assets",
                "Monitor activity",
            ]


        else:

            severity = "low"
            priority = "monitor"

            actions = [
                "Continue monitoring",
            ]



        result = {

            "case_id":
                case_id,


            "risk": {

                "severity":
                    severity,

                "priority":
                    priority,

            },


            "recommended_actions":
                actions,


            "confidence":
                confidence,


            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

        }


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ):

        return self.history.copy()



    def clear_history(
        self,
    ):

        self.history.clear()