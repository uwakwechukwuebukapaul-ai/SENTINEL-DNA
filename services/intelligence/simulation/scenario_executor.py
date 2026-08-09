"""
Scenario Executor

Connects attack simulations with
Sentinel DNA AI investigation pipeline.
"""

from typing import Any, Dict

from .simulation_result import SimulationResult


class ScenarioExecutor:
    """
    Executes SOC investigation scenarios.
    """


    def __init__(
        self,
        investigator_gateway=None,
    ):

        self.gateway = (
            investigator_gateway
        )


    def execute(
        self,
        scenario: Dict[str, Any],
    ) -> SimulationResult:

        if not self.gateway:

            return SimulationResult(
                scenario_name=scenario["name"],
                status="simulation_only",
                findings=scenario.get(
                    "expected_findings",
                    [],
                ),
                metadata=scenario,
            )


        response = (
            self.gateway
            .start_investigation(
                alert={
                    "category":
                        scenario["category"],

                    "severity":
                        scenario["severity"],

                    "indicators":
                        scenario["indicators"],
                },

                scenario=scenario["name"],
            )
        )


        return self._normalize(
            scenario,
            response,
        )


    def _normalize(
        self,
        scenario,
        response,
    ):

        return SimulationResult(
            scenario_name=scenario["name"],

            status=response.get(
                "status",
                "unknown",
            ),

            investigation_id=response.get(
                "investigation_id"
            ),

            metadata=response,
        )