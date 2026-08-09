"""
Sentinel DNA - Simulation Executor

Executes simulated security incidents.

Flow:

Scenario
    |
    v
Investigation Gateway
    |
    v
AI Investigation Runtime
    |
    v
Result
"""

from __future__ import annotations

from typing import Any


class SimulationExecutor:
    """
    Executes attack simulations.
    """

    def __init__(
        self,
        investigator_gateway=None
    ):
        self.investigator_gateway = (
            investigator_gateway
        )


    def execute(
        self,
        scenario: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a simulation.
        """

        investigation_input = {
            "scenario_id": scenario.get("id"),
            "category": scenario.get(
                "category"
            ),
            "severity": scenario.get(
                "severity"
            ),
            "artifacts": scenario.get(
                "artifacts",
                []
            ),
        }


        if self.investigator_gateway:

            result = (
                self.investigator_gateway
                .investigate(
                    investigation_input
                )
            )

        else:

            result = {
                "status": "simulated",
                "message":
                    "Investigator gateway unavailable"
            }


        return {
            "scenario": scenario.get(
                "name"
            ),
            "execution": result
        }