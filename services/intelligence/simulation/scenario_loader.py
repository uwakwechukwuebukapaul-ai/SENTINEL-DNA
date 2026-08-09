"""
Scenario Loader

Loads attack simulation scenarios
from JSON definitions.
"""

import json
from pathlib import Path


class ScenarioLoader:
    """
    Loads simulation scenarios.
    """

    def __init__(self, scenario_directory=None):

        if scenario_directory:
            self.scenario_directory = Path(scenario_directory)

        else:
            self.scenario_directory = (
                Path(__file__).parent / "scenarios"
            )


    def load(self, scenario_name: str) -> dict:

        scenario_file = (
            self.scenario_directory /
            f"{scenario_name}.json"
        )

        if not scenario_file.exists():
            raise FileNotFoundError(
                f"Scenario not found: {scenario_name}"
            )

        with open(
            scenario_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)


    def available_scenarios(self):

        return [
            file.stem
            for file in self.scenario_directory.glob(
                "*.json"
            )
        ]