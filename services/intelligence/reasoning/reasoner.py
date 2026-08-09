"""
Sentinel DNA Investigation Reasoner

Transforms investigation findings into analyst intelligence.
"""

from __future__ import annotations

from typing import Any


class InvestigationReasoner:
    """
    AI reasoning layer for SOC investigations.
    """


    def reason(
        self,
        investigation_result,
    ) -> dict[str, Any]:
        """
        Generate investigation intelligence.
        """

        findings = (
            investigation_result.findings
        )


        threat_type = (
            self._identify_threat(
                findings
            )
        )


        confidence = (
            self._calculate_confidence(
                findings
            )
        )


        return {

            "case_id":
                investigation_result.case_id,


            "threat_assessment":
                threat_type,


            "confidence":
                confidence,


            "attack_story":
                self._build_story(
                    findings
                ),


            "recommendations":
                self._recommend_actions(
                    findings
                ),
        }



    def _identify_threat(
        self,
        findings,
    ) -> str:

        if (
            "threat_intelligence"
            in findings
        ):
            return (
                "credential_phishing"
            )


        return "unknown"



    def _calculate_confidence(
        self,
        findings,
    ) -> float:

        scores = []


        for value in findings.values():

            if isinstance(value, dict):

                confidence = value.get(
                    "confidence"
                )

                if confidence:

                    scores.append(
                        float(confidence)
                    )


        if not scores:

            return 0.0


        return round(
            sum(scores)
            /
            len(scores)
            *
            100,
            2,
        )



    def _build_story(
        self,
        findings,
    ) -> list[str]:

        story = []


        if (
            "threat_intelligence"
            in findings
        ):

            story.append(
                "Threat intelligence identified malicious indicators"
            )


        if (
            "analysis_engine"
            in findings
        ):

            story.append(
                "AI analysis classified suspicious activity"
            )


        return story



    def _recommend_actions(
        self,
        findings,
    ) -> list[str]:

        actions = []


        if (
            "threat_intelligence"
            in findings
        ):

            actions.extend(
                [
                    "Block malicious indicators",
                    "Search environment for related activity",
                    "Review affected users",
                ]
            )


        return actions