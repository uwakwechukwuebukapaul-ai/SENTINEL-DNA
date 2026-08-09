"""
Sentinel DNA Risk Engine
"""


class RiskEngine:
    """
    Calculates investigation severity.
    """


    def calculate(
        self,
        result,
    ) -> tuple[int,float]:

        score = 0


        score += len(
            result.iocs
        ) * 25


        score += len(
            result.mitre_attack
        ) * 15


        if score > 100:
            score = 100


        confidence = (
            score / 100
        )


        return score, confidence