from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class KnowledgeEntity:
 organization_id:str; entity_type:str; name:str; description:str=""; confidence:float=.8; metadata:dict=field(default_factory=dict); id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class KnowledgeRelationship:
 organization_id:str; source_entity:str; target_entity:str; relationship_type:str; confidence:float=.8; evidence:list=field(default_factory=list); id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
