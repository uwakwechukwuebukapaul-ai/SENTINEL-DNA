"""
Simulation Runner

High level interface for
executing security scenarios.
"""


from .scenario_loader import ScenarioLoader
from .simulation_engine import SimulationEngine



class SimulationRunner:


    def __init__(
        self,
        loader=None,
        engine=None
    ):

        self.loader = (
            loader
            or ScenarioLoader()
        )

        self.engine = (
            engine
            or SimulationEngine()
        )


    def run(
        self,
        scenario_name: str
    ):


        scenario = (
            self.loader.load(
                scenario_name
            )
        )


        return self.engine.execute(
            scenario
        )