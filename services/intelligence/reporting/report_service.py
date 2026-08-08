"""
Sentinel DNA Investigation Report Service

Coordinates investigation report generation
and API response formatting.
"""

from __future__ import annotations

from typing import Any


class ReportService:
    """
    Application service for investigation reporting.
    """

    def __init__(
        self,
        report_generator=None,
        executive_summary=None,
        timeline_builder=None,
    ) -> None:

        self.report_generator = report_generator

        self.executive_summary = executive_summary

        self.timeline_builder = timeline_builder


    def create_report(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create investigation report.
        """

        if self.report_generator:

            report = self.report_generator.generate(
                investigation
            )

        else:

            case_id = investigation.get(
                "case_id",
                investigation.get(
                    "id",
                    "UNKNOWN",
                ),
            )

            report = {

                "case_id": case_id,

                "status": investigation.get(
                    "status",
                    "unknown",
                ),

                "severity": investigation.get(
                    "severity",
                    "unknown",
                ),

                "summary": (
                    f"Investigation {case_id} "
                    "report generated."
                ),

                "timeline": [],

                "results": investigation.get(
                    "results",
                    [],
                ),
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


        return report


    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compatibility API.
        """

        return self.create_report(
            investigation
        )


    def build_response(
        self,
        case_id: str,
        summary: dict[str, Any] | None = None,
        timeline: list[dict[str, Any]] | None = None,
        findings: list[Any] | None = None,
        artifacts: list[Any] | None = None,
        orchestration_result: dict[str, Any] | None = None,
        severity: str = "unknown",
    ) -> dict[str, Any]:
        """
        Build API-ready investigation report response.
        """

        return {

            "case_id": case_id,

            "severity": severity,

            "summary": (
                summary
                if summary is not None
                else {}
            ),

            "timeline": (
                timeline
                if timeline is not None
                else []
            ),

            "findings": (
                findings
                if findings is not None
                else []
            ),

            "artifacts": (
                artifacts
                if artifacts is not None
                else []
            ),

            "orchestration_result": (
                orchestration_result
                if orchestration_result is not None
                else {}
            ),

            "status": "completed",
        }