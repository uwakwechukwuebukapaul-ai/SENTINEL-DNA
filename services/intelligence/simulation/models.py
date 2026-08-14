from dataclasses import asdict,dataclass,field
@dataclass
class DigitalTwin:
 assets:list[dict]=field(default_factory=list); identities:list[dict]=field(default_factory=list); vulnerabilities:list[dict]=field(default_factory=list); controls:list[dict]=field(default_factory=list); attack_paths:list[dict]=field(default_factory=list)
 def to_dict(self): return asdict(self)
@dataclass
class SimulationScenario:
 scenario_id:str; title:str; changes:dict=field(default_factory=dict); description:str=""
 def to_dict(self): return asdict(self)
@dataclass
class SimulationResult:
 scenario_id:str; current_risk:int; projected_risk:int; control_impact:int; phases:list[str]=field(default_factory=list); explanation:str=""; synthetic_only:bool=True
 def to_dict(self): return asdict(self)
