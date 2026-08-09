"""
Sentinel DNA Investigation Narrative Generator.

Transforms investigation intelligence
outputs into analyst-readable reports.
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
        Generate analyst investigation narrative.
        """

        reasoning = intelligence.get(
            "reasoning",
            {},
        )

        correlation = intelligence.get(
            "correlation",
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


        findings = self._build_findings(
            intelligence
        )


        recommendations = (
            self._build_recommendations(
                classification
            )
        )


        return {

            "status":
                "completed",


            "summary":
                self._build_summary(
                    classification
                ),


            "severity":
                self._severity(
                    confidence
                ),


            "attack_stage":
                self._attack_stage(
                    classification
                ),


            "findings":
                findings,


            "recommendations":
                recommendations,


            "confidence":
                confidence,


            "correlation":
                correlation,
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
            "no confirmed classification."
        )



    def _build_findings(
        self,
        intelligence: dict[str, Any],
    ) -> list[str]:

        findings = []


        if intelligence.get(
            "indicators"
        ):

            findings.append(
                "Suspicious indicators identified."
            )


        reasoning = intelligence.get(
            "reasoning",
            {},
        )


        if reasoning.get(
            "classification"
        ) != "unknown":

            findings.append(
                "Threat classification generated "
                "by reasoning engine."
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
            ]


        return [
            "Continue monitoring activity."
        ]



    def _severity(
        self,
        confidence: float,
    ) -> str:

        if confidence >= 0.8:

            return "high"


        if confidence >= 0.5:

            return "medium"


        return "low"



    def _attack_stage(
        self,
        classification: str,
    ) -> str:

        if classification == "phishing":

            return "Initial Access"


        if classification == "malware":

            return "Execution"


        return "Unknown"