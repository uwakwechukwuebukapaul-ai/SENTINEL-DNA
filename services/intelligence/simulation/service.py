import hashlib
from .digital_twin import DigitalTwinBuilder
from .scenario import ScenarioEngine
from .attack_simulator import AttackSimulator
from .risk_projection import RiskProjectionEngine
from .models import SimulationScenario
class SimulationService:
 def __init__(self): self.builder=DigitalTwinBuilder(); self.scenarios=ScenarioEngine(); self.simulator=AttackSimulator(); self.projector=RiskProjectionEngine()
 def simulate(self,twin,scenario):
  copy=self.builder.build(**twin.to_dict()); copy=self.scenarios.apply(copy,scenario); phases=self.simulator.simulate(copy); current,projected,impact=self.projector.project(copy,phases); return __import__('services.intelligence.simulation.models',fromlist=['SimulationResult']).SimulationResult(scenario.scenario_id,current,projected,impact,phases,"Projected risk changes under the requested controls.")
 def create_scenario(self,title,changes): return SimulationScenario("SIM-"+hashlib.sha256(f"{title}|{changes}".encode()).hexdigest()[:16],title,changes)
