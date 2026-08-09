"""
Sentinel DNA Investigation Priority Engine
"""


class PriorityEngine:

    def calculate(
        self,
        risk: str,
    ) -> str:


        mapping = {

            "high": "urgent",

            "medium": "normal",

            "low": "low",

        }


        return mapping.get(
            risk,
            "normal",
        )