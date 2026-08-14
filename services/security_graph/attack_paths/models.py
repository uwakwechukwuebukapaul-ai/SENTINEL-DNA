from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
@dataclass
class AttackPathNode:
 entity_id:str; entity_type:str; role:str="intermediate"; exposure_level:str="unknown"
 def to_dict(self): return asdict(self)
@dataclass
class AttackPath:
 path_id:str; tenant_id:str; name:str; severity:str; confidence:float; nodes:list[AttackPathNode]=field(default_factory=list); relationships:list[str]=field(default_factory=list); risk_score:int=0; explanation:str=""; created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
 def to_dict(self): d=asdict(self); d["nodes"]=[n.to_dict() for n in self.nodes]; return d
@dataclass
class AttackPathFinding:
 source_entity:str; destination_entity:str; path:list[str]; confidence:float; reasoning:str
 def to_dict(self): return asdict(self)
