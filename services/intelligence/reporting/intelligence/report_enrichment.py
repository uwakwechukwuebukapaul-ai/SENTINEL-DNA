"""
Sentinel DNA Report Intelligence Enrichment

Adds security intelligence context
to investigation reports.

Responsibilities:

- enrich findings
- attach MITRE context
- attach threat intelligence
- calculate report metadata
- generate attack narrative
- generate analyst summary
"""

from __future__ import annotations

from typing import Any


class ReportEnrichment:
    """
    Investigation report intelligence enhancer.
    """


    def __init__(
        self,
        mitre_engine=None,
        threat_intelligence_engine=None,
        risk_engine=None,
        confidence_engine=None,
        attack_story_builder=None,
        analyst_summary_generator=None,
    ) -> None:

        self.mitre_engine = mitre_engine

        self.threat_intelligence_engine = (
            threat_intelligence_engine
        )

        self.risk_engine = risk_engine

        self.confidence_engine = (
            confidence_engine
        )

        self.attack_story_builder = (
            attack_story_builder
        )

        self.analyst_summary_generator = (
            analyst_summary_generator
        )


    def enrich(
        self,
        report: dict[str, Any],
        intelligence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Enrich investigation report.

        Supports:

            enrich(report)

        and legacy:

            enrich(report, intelligence)
        """

        enriched_report = dict(report)


        if intelligence is not None:

            enriched_report[
                "intelligence"
            ] = intelligence


        artifacts = enriched_report.get(
            "artifacts",
            [],
        )

        findings = enriched_report.get(
            "findings",
            [],
        )


        intelligence_context = (
            enriched_report.get(
                "intelligence",
                {},
            )
        )


        if not isinstance(
            intelligence_context,
            dict,
        ):

            intelligence_context = {}


        #
        # MITRE ATT&CK enrichment
        #

        intelligence_context[
            "mitre"
        ] = intelligence_context.get(
            "mitre",
            self._map_mitre(
                findings,
                artifacts,
            ),
        )


        #
        # Threat intelligence enrichment
        #

        intelligence_context[
            "threat_context"
        ] = intelligence_context.get(
            "threat_context",
            self._threat_context(
                artifacts,
            ),
        )


        #
        # Risk calculation
        #

        intelligence_context[
            "risk"
        ] = intelligence_context.get(
            "risk",
            self._calculate_risk(
                enriched_report,
            ),
        )


        #
        # Confidence scoring
        #

        intelligence_context[
            "confidence"
        ] = intelligence_context.get(
            "confidence",
            self._calculate_confidence(
                enriched_report,
            ),
        )


        enriched_report[
            "intelligence"
        ] = intelligence_context


        #
        # Intelligence lifecycle state
        #

        enriched_report[
            "intelligence_status"
        ] = "completed"


        enriched_report[
            "enrichment_status"
        ] = "completed"


        #
        # Attack narrative
        #

        if "attack_story" not in enriched_report:

            enriched_report[
                "attack_story"
            ] = self._build_attack_story(
                enriched_report,
                artifacts,
                findings,
            )


        #
        # Analyst summary
        #

        if "analyst_summary" not in enriched_report:

            enriched_report[
                "analyst_summary"
            ] = self._build_analyst_summary(
                enriched_report,
            )


        return enriched_report



    def _build_attack_story(
        self,
        report: dict[str, Any],
        artifacts: list[Any],
        findings: list[Any],
    ) -> dict[str, Any]:
        """
        Generate attacker activity narrative.
        """


        if self.attack_story_builder:

            return (
                self.attack_story_builder.build(
                    case_id=report.get(
                        "case_id"
                    ),
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

            "title":
                "Threat Activity Narrative",

            "summary":
                (
                    "Investigation identified "
                    "potential malicious activity "
                    "requiring analyst review."
                ),

            "indicators":
                indicators,

            "phases":
                [
                    "Detection",
                    "Evidence Collection",
                    "Threat Analysis",
                ],
        }



    def _build_analyst_summary(
        self,
        report: dict[str, Any],
    ) -> str:
        """
        Generate SOC analyst summary.
        """


        if self.analyst_summary_generator:

            return (
                self.analyst_summary_generator.generate(
                    report
                )
            )


        case_id = report.get(
            "case_id",
            "UNKNOWN",
        )

        status = report.get(
            "intelligence_status",
            "completed",
        )


        severity = report.get(
            "severity",
            "unknown",
        )


        return (
            f"Investigation {case_id} "
            f"completed with intelligence status "
            f"{status}. Severity classified as "
            f"{severity}. Evidence analysis, threat "
            "context enrichment, and investigation "
            "metadata generation completed."
        )



    def _map_mitre(
        self,
        findings,
        artifacts,
    ) -> list[Any]:

        if self.mitre_engine:

            return (
                self.mitre_engine.map(
                    findings=findings,
                    artifacts=artifacts,
                )
            )


        return []



    def _threat_context(
        self,
        artifacts,
    ) -> list[Any]:

        if self.threat_intelligence_engine:

            return (
                self.threat_intelligence_engine.enrich(
                    artifacts
                )
            )


        context = []


        for artifact in artifacts:

            if isinstance(
                artifact,
                dict,
            ):

                context.append(
                    {
                        "indicator":
                            artifact.get(
                                "value"
                            ),

                        "status":
                            "unverified",
                    }
                )


        return context



    def _calculate_risk(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:

        if self.risk_engine:

            return (
                self.risk_engine.calculate(
                    report
                )
            )


        return {

            "level":
                report.get(
                    "severity",
                    "unknown",
                ),

            "score":
                0,

        }



    def _calculate_confidence(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:

        if self.confidence_engine:

            return (
                self.confidence_engine.calculate(
                    report
                )
            )


        return {

            "level":
                "medium",

            "score":
                50,

        }