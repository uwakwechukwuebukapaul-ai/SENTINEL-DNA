"""
Sentinel DNA AI Investigator Demo Runner

Runs a complete simulated SOC investigation.

Usage:

python demo/demo_runner.py
"""

from __future__ import annotations

import sys
from pathlib import Path


# Add project root to Python path

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BASE_DIR)
    )


from services.intelligence.simulation import (
    ScenarioLoader,
    InvestigationSimulator,
)


from demo.demo_report import DemoReport


SCENARIO_PATH = (
    BASE_DIR
    /
    "services"
    /
    "intelligence"
    /
    "simulation"
    /
    "scenarios"
)



def build_simulator():

    loader = ScenarioLoader(
        SCENARIO_PATH
    )

    return InvestigationSimulator(
        loader
    )



def run_demo(
    scenario="phishing_attack"
):

    simulator = build_simulator()

    result = simulator.simulate(
        scenario
    )

    report = DemoReport()

    output = report.generate(
        result
    )

    print(output)

    return result



if __name__ == "__main__":

    run_demo()