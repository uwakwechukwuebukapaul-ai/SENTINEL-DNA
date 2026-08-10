"""
Sentinel DNA Investigation Report Generator.

Transforms fused investigation intelligence into a
stable, analyst-ready investigation report.
"""

from typing import Any

from .models import (
    InvestigationReport,
)


class InvestigationReportGenerator:
    """
    Generates structured investigation reports.

    This component is intentionally presentation-focused.
    Detection, correlation, threat intelligence, and reasoning
    remain responsibilities of their respective engines.
    """


    def generate(
        self,
        intelligence,
        case_id: str | None = None,
    ) -> InvestigationReport:
        """
        Generate an investigation report from fused intelligence.
        """

        data = self._normalize(
            intelligence
        )

        resolved_case_id = (
            case_id
            or data.get(
                "case_id",
                "UNKNOWN",
            )
        )

        risk = self._normalize_risk(
            data.get(
                "risk",
                "low",
            )
        )

        confidence = self._normalize_confidence(
            data.get(
                "confidence",
                50,
            )
        )

        findings = self._normalize_list(
            data.get(
                "findings",
                [],
            )
        )

        mitre_techniques = self._unique_strings(
            data.get(
                "mitre_techniques",
                [],
            )
        )

        recommendations = self._unique_strings(
            data.get(
                "recommendations",
                [],
            )
        )

        summary = data.get(
            "threat_summary",
            "",
        )

        if not summary:

            summary = self._build_summary(
                risk=risk,
                finding_count=len(
                    findings
                ),
                mitre_count=len(
                    mitre_techniques
                ),
            )

        title = self._build_title(
            risk
        )

        metadata = dict(
            data.get(
                "metadata",
                {},
            )
            or {}
        )

        metadata.update(
            {
                "report_type": (
                    "investigation_report"
                ),
                "finding_count": (
                    len(findings)
                ),
                "mitre_count": (
                    len(mitre_techniques)
                ),
                "recommendation_count": (
                    len(recommendations)
                ),
            }
        )

        return InvestigationReport(
            case_id=resolved_case_id,
            status="completed",
            title=title,
            summary=str(
                summary
            ),
            risk=risk,
            confidence=confidence,
            findings=findings,
            mitre_techniques=mitre_techniques,
            recommendations=recommendations,
            metadata=metadata,
        )


    def _normalize(
        self,
        intelligence,
    ) -> dict[str, Any]:
        """
        Accept both dataclass-style and dictionary-style
        fusion results.
        """

        if intelligence is None:

            return {}

        if isinstance(
            intelligence,
            dict,
        ):

            return dict(
                intelligence
            )

        to_dict = getattr(
            intelligence,
            "to_dict",
            None,
        )

        if callable(
            to_dict
        ):

            result = to_dict()

            if isinstance(
                result,
                dict,
            ):

                return result

        attributes = (
            "case_id",
            "risk",
            "confidence",
            "threat_summary",
            "findings",
            "mitre_techniques",
            "recommendations",
            "metadata",
        )

        return {
            name: getattr(
                intelligence,
                name,
                None,
            )
            for name in attributes
        }


    def _normalize_risk(
        self,
        risk,
    ) -> str:
        """
        Normalize risk labels into the supported contract.
        """

        value = str(
            risk or "low"
        ).lower().strip()

        allowed = {
            "critical",
            "high",
            "medium",
            "low",
            "unknown",
        }

        if value in allowed:

            return value

        return "unknown"


    def _normalize_confidence(
        self,
        confidence,
    ) -> int:
        """
        Normalize confidence to a bounded integer.
        """

        try:

            value = int(
                confidence
            )

        except (
            TypeError,
            ValueError,
        ):

            return 50

        return max(
            0,
            min(
                100,
                value,
            ),
        )


    def _normalize_list(
        self,
        values,
    ) -> list[Any]:
        """
        Normalize potentially missing collection values.
        """

        if values is None:

            return []

        if isinstance(
            values,
            list,
        ):

            return list(
                values
            )

        if isinstance(
            values,
            tuple,
        ):

            return list(
                values
            )

        return [
            values
        ]


    def _unique_strings(
        self,
        values,
    ) -> list[str]:
        """
        Remove duplicate string values while preserving order.
        """

        normalized = []

        for value in self._normalize_list(
            values
        ):

            text = str(
                value
            ).strip()

            if (
                text
                and text not in normalized
            ):

                normalized.append(
                    text
                )

        return normalized


    def _build_title(
        self,
        risk: str,
    ) -> str:
        """
        Generate a consistent report title.
        """

        if risk == "critical":

            return (
                "Critical Security Investigation"
            )

        if risk == "high":

            return (
                "High Risk Security Investigation"
            )

        if risk == "medium":

            return (
                "Security Investigation"
            )

        return (
            "Security Investigation Report"
        )


    def _build_summary(
        self,
        risk: str,
        finding_count: int,
        mitre_count: int,
    ) -> str:
        """
        Generate a deterministic fallback summary.
        """

        if risk in {
            "critical",
            "high",
        }:

            return (
                "The investigation identified "
                f"{finding_count} finding(s) with "
                f"{mitre_count} mapped MITRE ATT&CK "
                "technique(s). Further analyst "
                "investigation is recommended."
            )

        return (
            "The investigation produced "
            f"{finding_count} finding(s) with "
            f"{mitre_count} mapped MITRE ATT&CK "
            "technique(s). No immediate high-risk "
            "threat was established."
        )