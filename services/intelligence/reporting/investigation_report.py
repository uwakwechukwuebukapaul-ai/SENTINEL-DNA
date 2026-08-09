"""
Investigation Report Generator

Creates final investigation reports from
correlation, decision, and intelligence results.
"""


from datetime import datetime, timezone


class InvestigationReport:
    """
    Investigation reporting service.

    Responsibilities:
    - Build analyst-ready reports
    - Preserve investigation history
    - Provide serialization
    """


    def __init__(
        self,
        case_id: str = None,
        severity: str = "unknown",
        risk_score: float = 0.0,
        findings=None,
        recommendations=None,
        agent_results=None,
    ):

        self.case_id = case_id

        self.severity = severity

        self.risk_score = risk_score

        self.findings = findings or []

        self.recommendations = (
            recommendations or []
        )

        self.agent_results = (
            agent_results or {}
        )

        self.history = []



    def generate(
        self,
        investigation: dict,
    ) -> dict:
        """
        Generate investigation report.

        Compatible with:
        - correlation output
        - decision engine output
        - analyst dashboard
        """


        case_id = (
            investigation.get(
                "case_id",
                self.case_id,
            )
        )


        correlation = (
            investigation.get(
                "correlation",
                {},
            )
        )


        decision = (
            investigation.get(
                "decision",
                {},
            )
        )


        confidence = (
            correlation.get(
                "confidence",
                0.0,
            )
        )


        indicators = (
            correlation.get(
                "indicators",
                [],
            )
        )


        techniques = (
            correlation.get(
                "techniques",
                [],
            )
        )


        attack_story = (
            correlation.get(
                "attack_story",
                "",
            )
        )


        response = (
            decision.get(
                "decision",
                "monitor",
            )
        )


        risk_rating = (
            self._calculate_risk(
                confidence,
                indicators,
                response,
            )
        )


        report = {

            "status":
                "completed",


            "case_id":
                case_id,


            "risk_rating":
                risk_rating,


            "severity":
                risk_rating,


            "confidence":
                confidence,


            "attack_story":
                attack_story,


            "indicators":
                indicators,


            "techniques":
                techniques,


            "decision":
                response,


            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

        }


        self.history.append(
            report
        )


        return report



    def _calculate_risk(
        self,
        confidence,
        indicators,
        decision,
    ):

        if decision == "respond":
            return "critical"


        if confidence >= 0.8:
            return "high"


        if confidence >= 0.5:
            return "medium"


        if len(indicators) > 0:
            return "medium"


        return "low"



    def get_history(self):

        return self.history



    def clear_history(self):

        self.history.clear()



    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "severity":
                self.severity,

            "risk_score":
                self.risk_score,

            "findings":
                self.findings,

            "recommendations":
                self.recommendations,

            "agent_results":
                self.agent_results,

        }