"""
Sentinel DNA - Investigation Simulator

High level simulation service.

Used for:
- demonstrations
- testing
- analyst training
- product validation
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
        scenario_name: str
    ) -> dict:

        scenario = (
            self.loader.load(
                scenario_name
            )
        )

        result = (
            self.executor.execute(
                scenario
            )
        )


        return {
            "simulation": scenario_name,
            "status": "completed",
            "result": result
        }