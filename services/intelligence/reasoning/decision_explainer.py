"""
Decision Explanation Engine.

Creates human-readable analyst reasoning.
"""


class DecisionExplainer:


    def explain(
        self,
        hypothesis: dict,
        confidence: float,
    ) -> list[str]:


        reasons = []


        threat = hypothesis.get(
            "threat"
        )


        if threat == "credential_phishing":

            reasons.append(
                "Credential phishing indicators detected"
            )


        reasons.append(
            f"Reasoning confidence calculated at {confidence}"
        )


        return reasons