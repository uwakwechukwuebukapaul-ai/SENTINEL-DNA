"""
Sentinel DNA Intelligent Report Service

Coordinates advanced investigation reporting,
intelligence enrichment, attack narrative generation,
and API-ready report construction.
"""

from __future__ import annotations

from typing import Any


class IntelligentReportService:
    """
    Intelligent investigation reporting orchestrator.
    """

    def __init__(
        self,
        report_service=None,
        report_enrichment=None,
        attack_story_builder=None,
        analyst_summary_generator=None,
    ) -> None:

        self.report_service = report_service
        self.report_enrichment = report_enrichment
        self.attack_story_builder = attack_story_builder
        self.analyst_summary_generator = (
            analyst_summary_generator
        )


    def generate(
        self,
        case_id: str,
        orchestration_result: Any,
        artifacts: list[Any] | None = None,
        findings: list[Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate intelligent investigation report.
        """

        artifacts = artifacts or []
        findings = findings or []


        if hasattr(
            orchestration_result,
            "to_dict",
        ):
            orchestration_result = (
                orchestration_result.to_dict()
            )


        if not isinstance(
            orchestration_result,
            dict,
        ):
            orchestration_result = {
                "status": getattr(
                    orchestration_result,
                    "status",
                    "completed",
                )
            }


        status = orchestration_result.get(
            "status",
            "completed",
        )


        report = {

            "case_id": case_id,

            "status": status,

            "intelligence_status": status,

            "severity": (
                orchestration_result.get(
                    "severity",
                    "unknown",
                )
            ),

            "artifacts": artifacts,

            "findings": findings,

            "timeline": [],

            "attack_story": (
                self._build_attack_story(
                    case_id,
                    artifacts,
                    findings,
                )
            ),

            "analyst_summary": (
                self._build_summary(
                    case_id,
                    status,
                )
            ),
        }


        if self.report_enrichment:

            enriched = (
                self.report_enrichment.enrich(
                    report
                )
            )

            if isinstance(
                enriched,
                dict,
            ):
                report = enriched


        if self.report_service:

            report = self._merge_base_report(
                report
            )


        return report


    def _merge_base_report(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Safely integrate lower-level report service.
        """

        base_report = None


        if hasattr(
            self.report_service,
            "generate",
        ):

            base_report = (
                self.report_service.generate(
                    report
                )
            )


        elif hasattr(
            self.report_service,
            "create_report",
        ):

            base_report = (
                self.report_service.create_report(
                    report
                )
            )


        elif hasattr(
            self.report_service,
            "build_response",
        ):

            builder = (
                self.report_service.build_response
            )

            attempts = [

                lambda: builder(
                    case_id=report["case_id"],
                    summary=report,
                    timeline=report.get(
                        "timeline",
                        [],
                    ),
                    findings=report.get(
                        "findings",
                        [],
                    ),
                    artifacts=report.get(
                        "artifacts",
                        [],
                    ),
                ),

                lambda: builder(
                    report["case_id"],
                    report,
                    report.get(
                        "timeline",
                        [],
                    ),
                    report.get(
                        "findings",
                        [],
                    ),
                    report.get(
                        "artifacts",
                        [],
                    ),
                ),

                lambda: builder(
                    report["case_id"]
                ),

            ]


            for attempt in attempts:

                try:
                    base_report = attempt()
                    break

                except TypeError:
                    continue


        if isinstance(
            base_report,
            dict,
        ):

            report.update(
                base_report
            )


        return report


    def _build_attack_story(
        self,
        case_id: str,
        artifacts: list[Any],
        findings: list[Any],
    ) -> dict[str, Any]:
        """
        Create analyst-friendly attack narrative.
        """

        if self.attack_story_builder:

            return (
                self.attack_story_builder.build(
                    case_id=case_id,
                    artifacts=artifacts,
                    findings=findings,
                )
            )


        indicators = []


        for artifact in artifacts:

            if isinstance(
                artifact,
                dict,
            ):

                value = artifact.get(
                    "value"
                )

                if value:
                    indicators.append(
                        value
                    )


        return {

            "title": (
                "Investigation Attack Story"
            ),

            "summary": (
                f"Investigation {case_id} "
                "identified suspicious activity "
                "requiring analyst review."
            ),

            "indicators": indicators,

            "phases": [

                "Initial Detection",

                "Evidence Collection",

                "Threat Analysis",

            ],
        }


    def _build_summary(
        self,
        case_id: str,
        status: str,
    ) -> str:
        """
        Generate analyst summary.
        """

        if self.analyst_summary_generator:

            return (
                self.analyst_summary_generator.generate(
                    {
                        "case_id": case_id,
                        "status": status,
                    }
                )
            )


        return (
            f"Investigation {case_id} "
            f"completed with status {status}."
        )