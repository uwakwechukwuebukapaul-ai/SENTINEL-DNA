"""
Sentinel DNA Dashboard Adapter.

Transforms analyst investigation views
into dashboard-ready SOC payloads.

Responsibilities:

- Normalize investigation presentation data
- Provide stable dashboard contract
- Hide internal intelligence structures
- Prepare frontend/API consumption
"""

from __future__ import annotations

from typing import Any


class DashboardAdapter:
    """
    Dashboard presentation adapter.
    """


    def build(
        self,
        investigation_view: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build dashboard payload from
        analyst investigation view.
        """

        investigation_view = (
            investigation_view
            or {}
        )


        summary = (
            investigation_view.get(
                "summary",
                {},
            )
        )


        return {

            # ==========================================
            # CASE INFORMATION
            # ==========================================

            "case": {

                "case_id": (
                    investigation_view.get(
                        "case_id",
                    )
                ),

                "investigation_id": (
                    investigation_view.get(
                        "investigation_id",
                    )
                ),

                "status": (
                    investigation_view.get(
                        "status",
                        "unknown",
                    )
                ),

            },


            # ==========================================
            # RISK INFORMATION
            # ==========================================

            "risk": {

                "level": (
                    investigation_view.get(
                        "risk",
                        "unknown",
                    )
                ),

                "confidence": (
                    investigation_view.get(
                        "confidence",
                        0.0,
                    )
                ),

            },


            # ==========================================
            # DASHBOARD METRICS
            # ==========================================

            "metrics": {

                "findings": (
                    summary.get(
                        "finding_count",
                        0,
                    )
                ),

                "indicators": (
                    summary.get(
                        "indicator_count",
                        0,
                    )
                ),

            },


            # ==========================================
            # THREAT INTELLIGENCE
            # ==========================================

            "threat_intelligence": {

                "mitre": (
                    investigation_view.get(
                        "mitre",
                        [],
                    )
                ),

                "timeline": (
                    investigation_view.get(
                        "timeline",
                        [],
                    )
                ),

                "indicators": (
                    investigation_view.get(
                        "indicators",
                        [],
                    )
                ),

            },


            # ==========================================
            # ANALYST ACTIONS
            # ==========================================

            "actions": (
                investigation_view.get(
                    "recommendations",
                    [],
                )
            ),


            # ==========================================
            # REPORT
            # ==========================================

            "report": (
                investigation_view.get(
                    "report",
                    {},
                )
            ),


        }