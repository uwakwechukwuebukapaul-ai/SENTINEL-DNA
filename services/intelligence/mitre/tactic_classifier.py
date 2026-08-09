"""
MITRE ATT&CK tactic classifier.
"""


class TacticClassifier:
    """
    Determines ATT&CK tactic.
    """


    def classify(
        self,
        technique: dict,
    ) -> str:

        return technique.get(
            "tactic",
            "Unknown",
        )