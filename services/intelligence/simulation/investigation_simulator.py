"""
Sentinel DNA Investigation Simulator

Loads scenarios and executes investigations.
"""

from __future__ import annotations


class InvestigationSimulator:

    def __init__(
        self,
        loader,
        executor
    ):
        self.loader = loader
        self.executor = executor


    def simulate(
        self,
        scenario_name
    ):

        scenario = self.loader.load(
            scenario_name
        )


        execution_result = (
            self.executor.execute(
                scenario
            )
        )


        return {
            "scenario": scenario.get(
                "name",
                scenario_name
            ),

            "status": "completed",

            "execution": execution_result,

            "artifacts": scenario.get(
                "artifacts",
                []
            ),

            "severity": scenario.get(
                "severity",
                "UNKNOWN"
            ),

            "category": scenario.get(
                "category",
                "unknown"
            )
        }