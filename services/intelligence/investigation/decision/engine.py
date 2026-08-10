"""
Sentinel DNA Investigation Decision Engine.

Transforms investigation intelligence into
SOC analyst decisions.
"""

from .models import (
    DecisionResult,
)


class InvestigationDecisionEngine:
    """
    Autonomous SOC decision layer.
    """


    def decide(
        self,
        case_id: str,
        report=None,
    ) -> DecisionResult:
        """
        Generate investigation decision.
        """


        data = self._normalize(
            report
        )


        risk = str(
            data.get(
                "risk",
                "low",
            )
        ).lower()


        confidence = int(
            data.get(
                "confidence",
                50,
            )
        )


        findings = data.get(
            "findings",
            [],
        )


        if risk in (
            "critical",
            "high",
        ):

            decision = "ESCALATE"

            priority = "P1"

            actions = [

                "Contain affected assets",

                "Collect additional telemetry",

                "Review related indicators",

                "Begin incident response workflow",
            ]


            rationale = (
                "High-risk investigation "
                "requires immediate SOC escalation."
            )


        elif risk == "medium":

            decision = "INVESTIGATE"

            priority = "P2"

            actions = [

                "Perform additional analysis",

                "Validate indicators",

                "Monitor affected entities",
            ]


            rationale = (
                "Suspicious activity requires "
                "further analyst investigation."
            )


        else:

            decision = "MONITOR"

            priority = "P3"

            actions = [

                "Continue monitoring",

                "Maintain evidence collection",
            ]


            rationale = (
                "Current evidence does not "
                "indicate immediate threat."
            )


        return DecisionResult(

            case_id=case_id,

            decision=decision,

            priority=priority,

            rationale=rationale,

            actions=actions,

            confidence=confidence,

            metadata={

                "engine":
                    "investigation_decision_engine",

                "finding_count":
                    len(findings),

                "automation_ready":
                    risk in (
                        "critical",
                        "high",
                    ),
            },
        )



    def _normalize(
        self,
        report,
    ):

        if report is None:

            return {}


        if isinstance(
            report,
            dict,
        ):

            return report


        if hasattr(
            report,
            "to_dict",
        ):

            return report.to_dict()


        return {}