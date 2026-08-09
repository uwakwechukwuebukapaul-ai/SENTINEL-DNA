"""
AI Investigation Accuracy Scoring Engine
"""


class AccuracyScoring:


    def calculate(
        self,
        metrics
    ):

        evidence_score = (
            metrics.evidence_coverage()
        )

        accuracy_score = (
            metrics.finding_accuracy()
        )


        final_score = round(
            (
                evidence_score * 0.5
                +
                accuracy_score * 0.5
            ),
            2
        )


        return {

            "evidence_score":
                evidence_score,

            "accuracy_score":
                accuracy_score,

            "overall_score":
                final_score
        }