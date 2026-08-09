"""
Analyst Benchmark Engine

Compares investigation performance
against expected outcomes.
"""


class AnalystBenchmark:


    def compare(
        self,
        ai_score,
        analyst_score
    ):


        difference = round(
            ai_score -
            analyst_score,
            2
        )


        return {

            "ai_score":
                ai_score,

            "analyst_score":
                analyst_score,

            "difference":
                difference,

            "status":
                (
                    "AI superior"
                    if difference > 0
                    else
                    "Analyst superior"
                )
        }