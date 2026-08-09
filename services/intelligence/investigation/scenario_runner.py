"""
Sentinel DNA AI Investigation Scenario Runner

Provides realistic end-to-end investigation execution.

Purpose:
- simulate SOC alerts
- trigger autonomous investigation
- validate intelligence workflow
- generate analyst-ready output
"""

from __future__ import annotations

from typing import Any


class InvestigationScenarioRunner:
    """
    Executes predefined SOC investigation scenarios.
    """


    def __init__(
        self,
        controller=None,
    ) -> None:

        self.controller = controller

        self.scenarios: dict[
            str,
            dict[str, Any]
        ] = {

            "phishing_attack": {

                "id": "SCENARIO-PHISHING-001",

                "type": "phishing",

                "severity": "high",

                "source": "email_security",

                "alert": {

                    "title": (
                        "Suspicious credential "
                        "harvesting email"
                    ),

                    "sender": (
                        "security-alert@fake-domain.com"
                    ),

                    "url": (
                        "https://malicious-login.example"
                    ),

                    "indicators": [

                        "credential theft",

                        "suspicious domain",

                    ],
                },
            },


            "malware_execution": {

                "id": "SCENARIO-MALWARE-001",

                "type": "malware",

                "severity": "critical",

                "source": "endpoint",

                "alert": {

                    "title": (
                        "Unknown executable detected"
                    ),

                    "process": (
                        "payload.exe"
                    ),

                    "indicators": [

                        "unknown hash",

                        "suspicious execution",

                    ],
                },
            },
        }



    def register_scenario(
        self,
        name: str,
        scenario: dict[str, Any],
    ) -> None:
        """
        Add custom investigation scenario.
        """

        self.scenarios[name] = scenario



    def run(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        Execute investigation scenario.
        """

        if name not in self.scenarios:

            raise ValueError(
                f"Unknown scenario: {name}"
            )


        scenario = self.scenarios[name]


        if self.controller:

            result = (
                self.controller.investigate(
                    scenario
                )
            )

        else:

            result = {

                "scenario": name,

                "status": "simulated",

                "alert": scenario,

            }


        return {

            "scenario": name,

            "input": scenario,

            "result": result,

        }



    def available_scenarios(
        self,
    ) -> list[str]:
        """
        Return available scenarios.
        """

        return list(
            self.scenarios.keys()
        )