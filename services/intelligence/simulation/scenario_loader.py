"""
Sentinel DNA - Scenario Loader

Responsible for loading and validating
security simulation scenarios.

Simulation scenarios represent:
- phishing attacks
- malware incidents
- credential compromise
- threat campaigns

Enterprise purpose:
Provide a controlled attack dataset
for AI investigation testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ScenarioLoader:
    """
    Loads simulation scenarios from disk.
    """

    REQUIRED_FIELDS = {
        "id",
        "name",
        "description",
        "category",
        "severity",
        "artifacts",
    }

    def __init__(self, scenario_directory: str | Path):
        self.scenario_directory = Path(scenario_directory)

    def load(self, scenario_name: str) -> dict[str, Any]:
        """
        Load scenario JSON file.
        """

        scenario_path = (
            self.scenario_directory /
            f"{scenario_name}.json"
        )

        if not scenario_path.exists():
            raise FileNotFoundError(
                f"Scenario not found: {scenario_name}"
            )

        with open(
            scenario_path,
            "r",
            encoding="utf-8"
        ) as file:
            scenario = json.load(file)

        self.validate(scenario)

        return scenario


    def validate(
        self,
        scenario: dict[str, Any]
    ) -> bool:
        """
        Validate scenario schema.
        """

        missing = (
            self.REQUIRED_FIELDS -
            scenario.keys()
        )

        if missing:
            raise ValueError(
                f"Invalid scenario. Missing fields: {missing}"
            )

        return True


    def list_scenarios(self) -> list[str]:
        """
        Return available scenarios.
        """

        if not self.scenario_directory.exists():
            return []

        return [
            file.stem
            for file in self.scenario_directory.glob(
                "*.json"
            )
        ]