"""
Sentinel DNA Investigation Reasoning Engine.

Transforms findings into investigation decisions.
"""


from .models import (
    ReasoningResult,
)


class InvestigationReasoningEngine:
    """
    Produces analyst-style investigation reasoning.
    """


    def analyze(
        self,
        findings,
    ):

        risk = "low"
        confidence = 50

        reasoning = []

        recommendations = []


        for finding in findings:

            if isinstance(
                finding,
                dict,
            ):

                finding_risk = (
                    finding.get(
                        "risk",
                        "low",
                    )
                )

                category = (
                    finding.get(
                        "category",
                        "unknown",
                    )
                )

            else:

                finding_risk = "low"
                category = "unknown"


            if finding_risk == "high":

                risk = "high"
                confidence = 85

                reasoning.append(
                    f"High risk indicator detected: {category}"
                )

                recommendations.append(
                    "Investigate affected assets"
                )


        if not reasoning:

            reasoning.append(
                "No high confidence threat indicators identified"
            )

            recommendations.append(
                "Continue monitoring"
            )


        return ReasoningResult(
            conclusion=(
                "Potential security incident"
                if risk == "high"
                else
                "No immediate threat identified"
            ),
            risk=risk,
            confidence=confidence,
            reasoning=reasoning,
            recommendations=list(
                set(recommendations)
            ),
        )