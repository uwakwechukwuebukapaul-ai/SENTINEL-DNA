from dataclasses import asdict,dataclass,field
@dataclass
class WorkflowContext:
 case_id:str; state:str="CREATED"; severity:str="unknown"; threat_type:str=""; asset_criticality:str="medium"; mitre_techniques:list[str]=field(default_factory=list); attack_path_risk:int=0; recommended_agents:list[str]=field(default_factory=list); approval_required:bool=False
 def to_dict(self): return asdict(self)
