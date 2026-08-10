"""
Investigation API Schemas.

Defines normalized API response contracts
for Sentinel DNA investigations.
"""

from __future__ import annotations

from typing import Any


class InvestigationResponseSchema:
    """
    Enterprise investigation response formatter.
    """


    @staticmethod
    def build(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize investigation result.

        Keeps API response stable even when
        intelligence modules evolve.
        """


        return {

            "investigation_id": (
                result.get(
                    "investigation_id"
                )
            ),


            "case_id": (
                result.get(
                    "case_id"
                )
            ),


            "status": (
                result.get(
                    "status",
                    "completed",
                )
            ),


            "success": (
                result.get(
                    "success",
                    True,
                )
            ),


            "risk": {

                "level": (
                    result.get(
                        "risk",
                        result.get(
                            "severity",
                            "unknown",
                        ),
                    )
                ),


                "score": (
                    result.get(
                        "risk_score",
                        0,
                    )
                ),

            },


            "confidence": (
                result.get(
                    "confidence",
                    0,
                )
            ),


            "findings": (
                result.get(
                    "findings",
                    [],
                )
            ),


            "indicators": (
                result.get(
                    "indicators",
                    [],
                )
            ),


            "mitre": (
                result.get(
                    "mitre",
                    [],
                )
            ),


            "timeline": (
                result.get(
                    "timeline",
                    [],
                )
            ),


            "recommendations": (
                result.get(
                    "recommendations",
                    [],
                )
            ),


            "report": (
                result.get(
                    "report",
                    {},
                )
            ),

        }