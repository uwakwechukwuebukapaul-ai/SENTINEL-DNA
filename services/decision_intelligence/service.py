"""
Sentinel DNA Decision Intelligence Service.

Provides:
- Security decision evaluation
- Risk-based recommendations
- Explainable reasoning
- Decision history tracking
- Legacy compatibility contracts
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from typing import Any



class DecisionIntelligenceService:
    """
    AI-assisted security decision engine.

    Supported APIs:

    Modern:
        decide()

    Legacy:
        evaluate()

    History:
        history()
        scoped()
    """



    def __init__(self) -> None:

        self.decisions: list[
            dict[str, Any]
        ] = []



    @staticmethod
    def _calculate_confidence(
        data: dict[str, Any],
    ) -> float:
        """
        Calculate decision confidence.

        Maintains legacy Sentinel DNA behavior:

        High risk + threat indicators =
        100 confidence

        Modern explicit confidence values
        remain supported.
        """


        if "confidence" in data:

            return round(
                float(
                    data["confidence"]
                ),
                2,
            )


        risk = float(
            data.get(
                "risk_score",
                0,
            )
        )


        threat_level = str(
            data.get(
                "threat_level",
                "",
            )
        ).lower()


        matches = data.get(
            "matches",
            [],
        )


        if (
            risk >= 80
            and threat_level in {
                "high",
                "critical",
            }
            and matches
        ):

            return 100



        if risk >= 80:

            return 90



        if risk >= 50:

            return 75



        return 50



    def decide(
        self,
        org: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a security decision.
        """


        risk = float(
            data.get(
                "risk_score",
                50,
            )
        )


        impact = float(
            data.get(
                "business_impact",
                50,
            )
        )


        decision_score = round(
            (
                risk +
                impact
            ) / 2,
            2,
        )



        result = {

            "type":
                "security_decision",


            "id":
                str(
                    uuid4()
                ),


            "organization_id":
                org,


            "decision":
                (
                    "Human-approved containment recommended"
                    if decision_score >= 65
                    else
                    "Continue monitoring and collect evidence"
                ),


            "confidence":
                self._calculate_confidence(
                    data
                ),


            "risk_score":
                risk,


            "impact_score":
                impact,


            "decision_score":
                decision_score,


            "reasoning_chain":
                [

                    "Context fused from security signals",

                    "Risk compared with business impact",

                    "Response alternatives ranked",

                ],


            "evidence":
                data.get(
                    "evidence",
                    [],
                ),


            "matches":
                data.get(
                    "matches",
                    [],
                ),


            "threat_level":
                data.get(
                    "threat_level",
                    "unknown",
                ),


            "recommended_actions":
                [

                    {
                        "action":
                            "containment",

                        "rank":
                            1,

                        "reason":
                            "Reduce immediate exposure",

                        "requires_approval":
                            True,
                    },


                    {
                        "action":
                            "monitoring",

                        "rank":
                            2,

                        "reason":
                            "Preserve service availability",

                        "requires_approval":
                            False,
                    },

                ],


            "alternatives":
                [

                    "Contain affected identity",

                    "Increase monitoring",

                    "Request analyst review",

                ],


            "human_approval_required":
                decision_score >= 65,


            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

        }



        self.decisions.append(
            result
        )


        return result



    def evaluate(
        self,
        context: dict[str, Any],
        evidence: dict[str, Any],
        intelligence: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Legacy Sentinel DNA evaluation API.

        Existing modules call:

            evaluate(
                context,
                evidence,
                intelligence
            )
        """


        merged: dict[str, Any] = {}



        if isinstance(
            context,
            dict,
        ):

            merged.update(
                context
            )



        if isinstance(
            evidence,
            dict,
        ):

            merged.update(
                evidence
            )



        if isinstance(
            intelligence,
            dict,
        ):

            merged.update(
                intelligence
            )



        organization_id = (

            context.get(
                "organization_id"
            )
            if isinstance(
                context,
                dict,
            )
            else None

        ) or "default"



        return self.decide(
            organization_id,
            merged,
        )



    def history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return complete decision history.
        """

        return self.decisions



    def scoped(
        self,
        org: str,
    ) -> list[dict[str, Any]]:
        """
        Return organization-specific decisions.
        """


        return [

            decision

            for decision in self.decisions

            if decision.get(
                "organization_id"
            )
            == org

        ]