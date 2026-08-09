"""
Feedback Engine

Processes analyst and evaluation feedback.
"""


class FeedbackEngine:


    def analyze(
        self,
        evaluation
    ):


        score = evaluation.get(
            "overall_score",
            0
        )


        if score >= 90:

            recommendation = (
                "Maintain current strategy"
            )

        elif score >= 70:

            recommendation = (
                "Optimize investigation workflow"
            )

        else:

            recommendation = (
                "Retrain investigation logic"
            )


        return {

            "score":
                score,

            "recommendation":
                recommendation
        }