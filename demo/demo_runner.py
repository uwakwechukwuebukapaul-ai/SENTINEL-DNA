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
    SimulationExecutor,
    InvestigationSimulator,
)


from services.intelligence.simulation.simulation_investigator_bridge import (
    SimulationInvestigatorBridge,
)


from services.intelligence.investigation.investigator_gateway import (
    InvestigatorGateway,
)


from services.intelligence.investigation.investigation_service import (
    InvestigationService,
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
    """
    Build Sentinel DNA simulation pipeline.

    Flow:

    ScenarioLoader
        |
        v
    SimulationExecutor
        |
        v
    SimulationInvestigatorBridge
        |
        v
    InvestigatorGateway
        |
        v
    InvestigationService
    """

    loader = ScenarioLoader(
        SCENARIO_PATH
    )


    # Real investigation service

    investigation_service = (
        InvestigationService()
    )


    # Enterprise gateway boundary

    gateway = InvestigatorGateway(
        orchestrator=investigation_service
    )


    # Bridge simulation layer
    # with investigation layer

    bridge = SimulationInvestigatorBridge(
        investigator_gateway=gateway
    )


    # Executor uses bridge

    executor = SimulationExecutor(
        bridge=bridge
    )


    return InvestigationSimulator(
        loader,
        executor
    )



def run_demo(
    scenario: str = "phishing_attack"
):
    """
    Execute SOC simulation.
    """

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