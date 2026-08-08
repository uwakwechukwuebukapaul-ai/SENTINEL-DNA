"""
Sentinel DNA Investigation Report Generator

Combines investigation intelligence outputs
into a final analyst investigation report.
"""

from __future__ import annotations

from typing import Any


class ReportGenerator:
    """
    Generates complete investigation reports.
    """

    def __init__(
        self,
        executive_summary=None,
        timeline_builder=None,
    ) -> None:

        self.executive_summary = (
            executive_summary
        )

        self.timeline_builder = (
            timeline_builder
        )

        self.history: list[
            dict[str, Any]
        ] = []


    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate investigation report.
        """

        case_id = investigation.get(
            "case_id",
            "UNKNOWN",
        )


        report = {

            "case_id": case_id,

            "status": investigation.get(
                "status",
                "unknown",
            ),

            "results": investigation.get(
                "results",
                [],
            ),

            "summary": (
                f"Investigation {case_id} "
                "report generated."
            ),

            "timeline": [],

        }


        if self.executive_summary:

            report[
                "executive_summary"
            ] = self.executive_summary.generate(
                investigation
            )


        if self.timeline_builder:

            report[
                "timeline"
            ] = self.timeline_builder.build(
                investigation
            )

        else:

            report[
                "timeline"
            ] = [
                {
                    "event": (
                        "Investigation created"
                    ),

                    "case_id": case_id,

                    "status": report["status"],
                }
            ]


        self.history.append(
            report
        )


        return report


    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return report history.
        """

        return self.history


    def clear_history(
        self,
    ) -> None:
        """
        Clear report history.
        """

        self.history.clear()