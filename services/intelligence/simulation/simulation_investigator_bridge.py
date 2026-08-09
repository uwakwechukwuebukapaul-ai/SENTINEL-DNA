"""
Sentinel DNA Simulation Investigator Bridge

Enterprise adapter between simulation scenarios
and the AI Investigator Gateway.

Responsibilities:

- Convert simulation scenarios into investigation alerts
- Invoke InvestigatorGateway
- Normalize investigation responses

This prevents simulation code from directly
depending on internal investigation engines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


class SimulationInvestigatorBridge:
    """
    Adapter connecting simulation execution
    with InvestigatorGateway.
    """

    def __init__(
        self,
        investigator_gateway=None,
    ):
        self.investigator_gateway = (
            investigator_gateway
        )


    def execute(
        self,
        scenario: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute investigation simulation.
        """

        scenario_name = scenario.get(
            "name",
            "unknown",
        )

        if not self.investigator_gateway:

            return {
                "status": "simulated",
                "message":
                    "Investigator gateway unavailable",
                "scenario":
                    scenario_name,
                "timestamp":
                    self._timestamp(),
            }


        alert = self._create_alert(
            scenario
        )


        result = (
            self.investigator_gateway
            .start_investigation(
                alert=alert,
                scenario=scenario_name,
                metadata={
                    "simulation": True,
                    "simulation_id":
                        scenario.get("id"),
                },
            )
        )


        return {
            "status": "completed",
            "scenario":
                scenario_name,
            "execution":
                result,
            "timestamp":
                self._timestamp(),
        }


    def _create_alert(
        self,
        scenario: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert simulation scenario into
        standard investigation alert format.
        """

        return {
            "source":
                "sentinel-dna-simulation",

            "severity":
                scenario.get(
                    "severity",
                    "UNKNOWN",
                ),

            "category":
                scenario.get(
                    "category",
                    "unknown",
                ),

            "description":
                scenario.get(
                    "description",
                    "",
                ),

            "artifacts":
                scenario.get(
                    "artifacts",
                    [],
                ),

            "expected_detection":
                scenario.get(
                    "expected_detection",
                    {},
                ),

            "expected_response":
                scenario.get(
                    "expected_response",
                    [],
                ),
        }


    @staticmethod
    def _timestamp() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()