"""
Sentinel DNA Investigation Narrative Generator.

Transforms investigation intelligence outputs
into analyst-readable security narratives.
"""

from __future__ import annotations

from typing import Any


class NarrativeGenerator:
    """
    Enterprise investigation narrative engine.
    """

    def generate(
        self,
        intelligence: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate investigation narrative.
        """

        reasoning = intelligence.get(
            "reasoning",
            {},
        )

        classification = reasoning.get(
            "classification",
            "unknown",
        )

        confidence = intelligence.get(
            "confidence",
            0.0,
        )

        return {
            "status": "completed",

            "summary": self._build_summary(
                classification
            ),

            "severity": self._calculate_severity(
                confidence
            ),

            "attack_stage": self._determine_attack_stage(
                classification
            ),

            "findings": self._build_findings(
                intelligence
            ),

            "recommendations": self._build_recommendations(
                classification
            ),

            "confidence": confidence,

            "correlation": intelligence.get(
                "correlation",
                {},
            ),
        }


    def _build_summary(
        self,
        classification: str,
    ) -> str:

        if classification == "phishing":

            return (
                "Potential phishing activity "
                "detected through investigation analysis."
            )

        if classification == "malware":

            return (
                "Potential malware activity "
                "identified during analysis."
            )

        return (
            "Investigation completed with "
            "insufficient threat classification."
        )


    def _build_findings(
        self,
        intelligence: dict[str, Any],
    ) -> list[str]:

        findings = []

        indicators = intelligence.get(
            "indicators",
            [],
        )

        if indicators:

            findings.append(
                "Suspicious indicators identified."
            )

        reasoning = intelligence.get(
            "reasoning",
            {},
        )

        if reasoning.get(
            "classification",
            "unknown",
        ) != "unknown":

            findings.append(
                "Threat classification generated "
                "by AI reasoning engine."
            )

        if not findings:

            findings.append(
                "No significant findings generated."
            )

        return findings


    def _build_recommendations(
        self,
        classification: str,
    ) -> list[str]:

        if classification == "phishing":

            return [
                "Block malicious indicators.",
                "Review affected user accounts.",
                "Reset exposed credentials.",
            ]

        if classification == "malware":

            return [
                "Isolate affected endpoint.",
                "Perform malware investigation.",
                "Collect endpoint evidence.",
            ]

        return [
            "Continue monitoring activity.",
            "Collect additional intelligence.",
        ]


    def _calculate_severity(
        self,
        confidence: float,
    ) -> str:

        if confidence >= 0.8:

            return "high"

        if confidence >= 0.5:

            return "medium"

        return "low"


    def _determine_attack_stage(
        self,
        classification: str,
    ) -> str:

        if classification == "phishing":

            return "Initial Access"

        if classification == "malware":

            return "Execution"

        return "Unknown"