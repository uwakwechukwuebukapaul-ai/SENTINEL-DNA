"""
Sentinel DNA Investigation View.

Transforms workspace data into
analyst-facing investigation representation.
"""

from __future__ import annotations

from typing import Any



class InvestigationView:
    """
    Analyst investigation presentation layer.
    """


    def render(
        self,
        workspace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate analyst view payload.
        """

        workspace = workspace or {}


        findings = workspace.get(
            "findings",
            [],
        )


        indicators = workspace.get(
            "indicators",
            [],
        )


        return {

            "case_id": (
                workspace.get(
                    "case_id"
                )
            ),


            "investigation_id": (
                workspace.get(
                    "investigation_id"
                )
            ),


            "status": (
                workspace.get(
                    "status",
                    "unknown",
                )
            ),


            "risk": (
                workspace.get(
                    "risk",
                    "unknown",
                )
            ),


            "confidence": (
                workspace.get(
                    "confidence",
                    0,
                )
            ),


            "summary": {

                "finding_count": len(
                    findings
                ),

                "indicator_count": len(
                    indicators
                ),

            },


            "findings": findings,


            "indicators": indicators,


            "mitre": (
                workspace.get(
                    "mitre",
                    [],
                )
            ),


            "timeline": (
                workspace.get(
                    "timeline",
                    [],
                )
            ),


            "recommendations": (
                workspace.get(
                    "recommendations",
                    [],
                )
            ),


            "report": (
                workspace.get(
                    "report",
                    {},
                )
            ),

        }