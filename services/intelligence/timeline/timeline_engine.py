"""Sentinel DNA investigation timeline generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .timeline_models import InvestigationTimelineEvent


class InvestigationTimelineEngine:
    """
    Investigation timeline generator.

    Supports:

    Modern contract:
        intelligence dict payload

    Legacy contract:
        list of timeline event dictionaries
    """

    @staticmethod
    def _timestamp(index: int) -> str:
        return datetime.fromtimestamp(
            index,
            timezone.utc,
        ).isoformat()


    @staticmethod
    def _normalize_list(
        value: Any,
    ) -> list[Any]:

        if value is None:
            return []

        if isinstance(value, list):
            return value

        return [value]


    def generate(
        self,
        intelligence: Any,
        alert: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        alert = alert or {}


        #
        # Legacy timeline events
        #
        if isinstance(
            intelligence,
            list,
        ):

            events = []

            for index, item in enumerate(
                intelligence,
                start=1,
            ):

                if not isinstance(
                    item,
                    dict,
                ):
                    continue


                events.append(
                    InvestigationTimelineEvent(
                        self._timestamp(index),
                        item.get(
                            "type",
                            "unknown",
                        ),
                        item.get(
                            "source",
                            "legacy",
                        ),
                        item.get(
                            "description",
                            "",
                        ),
                        alert.get(
                            "severity",
                            "info",
                        ),
                        item.get(
                            "iocs",
                            [],
                        ),
                    )
                )


            return [
                event.to_dict()
                for event in events
            ]



        #
        # Modern intelligence payload
        #

        intelligence = (
            intelligence
            if isinstance(
                intelligence,
                dict,
            )
            else {}
        )


        iocs = self._normalize_list(
            intelligence.get(
                "iocs"
            )
        )


        techniques = self._normalize_list(
            intelligence.get(
                "mitre_techniques"
            )
        )


        findings = [
            str(item)
            for item in self._normalize_list(
                intelligence.get(
                    "findings"
                )
            )
        ]


        recommendations = self._normalize_list(
            intelligence.get(
                "recommendations"
            )
        )


        severity = (
            intelligence.get(
                "risk_severity"
            )
            or alert.get(
                "severity"
            )
            or "info"
        )


        events = []


        events.append(
            InvestigationTimelineEvent(
                self._timestamp(1),
                "alert_received",
                "alert_ingestion",
                "Alert received",
                severity,
                iocs,
            )
        )


        if any(
            "failed" in item.lower()
            or "authentication" in item.lower()
            for item in findings
        ):

            events.append(
                InvestigationTimelineEvent(
                    self._timestamp(2),
                    "authentication_failure",
                    "evidence_analysis",
                    "Authentication failures detected",
                    severity,
                    iocs,
                )
            )


        if any(
            "ioc" in item.lower()
            or "indicator" in item.lower()
            for item in findings
        ):

            events.append(
                InvestigationTimelineEvent(
                    self._timestamp(3),
                    "suspicious_ioc",
                    "ioc_enrichment",
                    "Suspicious external IP identified",
                    severity,
                    iocs,
                )
            )


        for technique in techniques:

            events.append(
                InvestigationTimelineEvent(
                    self._timestamp(4),
                    "mitre_mapping",
                    "mitre_mapping",
                    f"MITRE {technique} mapped",
                    severity,
                    iocs,
                    [
                        technique
                    ],
                )
            )


        if recommendations:

            events.append(
                InvestigationTimelineEvent(
                    self._timestamp(5),
                    "recommendation",
                    "recommendations",
                    "Recommended response generated",
                    severity,
                    iocs,
                    techniques,
                    {
                        "recommendations": recommendations
                    },
                )
            )


        return [
            event.to_dict()
            for event in sorted(
                events,
                key=lambda item: item.timestamp,
            )
        ]



# Backward compatibility
TimelineEngine = InvestigationTimelineEngine