from dataclasses import asdict, dataclass, field
from uuid import uuid4
@dataclass
class SecurityNode:
    organization_id:str; entity_id:str; entity_type:str; attributes:dict=field(default_factory=dict); id:str=field(default_factory=lambda:str(uuid4()))
    def public(self): return asdict(self)
@dataclass
class SecurityRelationship:
    organization_id:str; source_id:str; relation:str; target_id:str; attributes:dict=field(default_factory=dict); id:str=field(default_factory=lambda:str(uuid4()))
    def public(self): return asdict(self)
