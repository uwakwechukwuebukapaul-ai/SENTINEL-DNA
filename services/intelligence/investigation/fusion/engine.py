"""
Sentinel DNA Investigation Intelligence Fusion Engine.

Combines multiple intelligence sources into
one investigation intelligence object.
"""

from .models import (
    InvestigationIntelligence,
)


class InvestigationFusionEngine:
    """
    Creates unified investigation intelligence.
    """


    def fuse(
        self,
        case_id: str,
        findings=None,
        reasoning=None,
        threat_intelligence=None,
    ):

        findings = findings or []

        mitre = []

        recommendations = []


        risk = "low"

        confidence = 50


        if reasoning:

            risk = getattr(
                reasoning,
                "risk",
                "low",
            )

            confidence = getattr(
                reasoning,
                "confidence",
                50,
            )


            recommendations.extend(
                getattr(
                    reasoning,
                    "recommendations",
                    [],
                )
            )


        normalized_findings = []


        for finding in findings:

            if hasattr(
                finding,
                "to_dict",
            ):

                item = (
                    finding.to_dict()
                )

            else:

                item = finding


            normalized_findings.append(
                item
            )


            if isinstance(
                item,
                dict,
            ):

                techniques = item.get(
                    "attack_patterns",
                    [],
                )

                mitre.extend(
                    techniques
                )


        if threat_intelligence:

            if isinstance(
                threat_intelligence,
                dict,
            ):

                mitre.extend(
                    threat_intelligence.get(
                        "mitre_techniques",
                        [],
                    )
                )


        if risk == "high":

            summary = (
                "Potential security incident "
                "requiring investigation"
            )

        else:

            summary = (
                "No immediate high-risk "
                "threat identified"
            )


        return InvestigationIntelligence(

            case_id=case_id,

            risk=risk,

            confidence=confidence,

            threat_summary=summary,

            findings=normalized_findings,

            mitre_techniques=list(
                set(mitre)
            ),

            recommendations=list(
                set(recommendations)
            ),

            metadata={
                "engine": (
                    "investigation_fusion"
                ),
                "finding_count": (
                    len(normalized_findings)
                ),
            },
        )