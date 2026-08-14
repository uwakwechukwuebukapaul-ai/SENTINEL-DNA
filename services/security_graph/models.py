from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from typing import Any
@dataclass
class GraphEntity:
 entity_id:str; tenant_id:str; entity_type:str; name:str; description:str=""; metadata:dict[str,Any]=field(default_factory=dict); created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
 def to_dict(self): return asdict(self)
@dataclass
class GraphRelationship:
 relationship_id:str; tenant_id:str; source_entity_id:str; target_entity_id:str; relationship_type:str; confidence:float=.0; evidence_reference:str=""; created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
 def to_dict(self): return asdict(self)
