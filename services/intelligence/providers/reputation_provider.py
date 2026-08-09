"""
Unified reputation intelligence provider.
"""


from typing import Any


class ReputationProvider:


    name = "reputation"


    def __init__(
        self,
        providers=None,
    ):

        self.providers = (
            providers
            or []
        )


    def lookup(
        self,
        indicator: str,
        indicator_type: str,
    ) -> dict[str, Any]:

        results = []


        for provider in self.providers:

            results.append(

                provider.lookup(
                    indicator,
                    indicator_type,
                )

            )


        if not results:

            return {

                "indicator": indicator,

                "type": indicator_type,

                "reputation": "unknown",

                "confidence": 0,

            }


        confidence = max(
            item.get(
                "confidence",
                0,
            )
            for item in results
        )


        malicious = any(
            item.get(
                "malicious",
                False,
            )
            for item in results
        )


        return {

            "indicator": indicator,

            "type": indicator_type,

            "reputation": (
                "malicious"
                if malicious
                else "unknown"
            ),

            "confidence": confidence,

            "sources": results,

        }