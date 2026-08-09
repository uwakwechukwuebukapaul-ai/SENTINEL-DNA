"""
Autonomous Investigation Evaluator

Coordinates evaluation workflow.
"""


from .investigation_metrics import (
    InvestigationMetrics
)

from .accuracy_scoring import (
    AccuracyScoring
)

from .evaluation_report import (
    EvaluationReport
)



class InvestigationEvaluator:


    def __init__(self):

        self.scorer = (
            AccuracyScoring()
        )


    def evaluate(
        self,
        investigation_id,
        evidence_found,
        expected_evidence,
        correct_findings,
        total_findings
    ):


        metrics = InvestigationMetrics(

            evidence_found=
                evidence_found,

            expected_evidence=
                expected_evidence,

            correct_findings=
                correct_findings,

            total_findings=
                total_findings
        )


        score = (
            self.scorer.calculate(
                metrics
            )
        )


        report = EvaluationReport(

            investigation_id=
                investigation_id,

            score=
                score
        )


        if score["overall_score"] >= 90:

            report.add_observation(
                "Excellent AI investigation performance"
            )

        elif score["overall_score"] >= 70:

            report.add_observation(
                "Acceptable investigation performance"
            )

        else:

            report.add_observation(
                "Investigation requires improvement"
            )


        return report