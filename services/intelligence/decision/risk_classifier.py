"""
Sentinel DNA Risk Classifier
"""


class RiskClassifier:

    def classify(
        self,
        alert: dict,
    ) -> str:

        severity = (
            alert.get(
                "severity",
                "low",
            )
            .lower()
        )


        if severity in (
            "critical",
            "high",
        ):
            return "high"


        if severity == "medium":
            return "medium"


        return "low"