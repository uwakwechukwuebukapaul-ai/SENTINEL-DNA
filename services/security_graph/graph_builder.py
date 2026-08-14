import hashlib
from .models import GraphEntity,GraphRelationship
class GraphBuilder:
 def entity(self,tenant_id,kind,name,metadata=None): return GraphEntity(hashlib.sha256(f"{tenant_id}|{kind}|{name}".encode()).hexdigest()[:16],tenant_id,kind,name,metadata=metadata or {})
 def relationship(self,tenant_id,source,target,kind,confidence=.8,evidence=""): return GraphRelationship(hashlib.sha256(f"{tenant_id}|{source.entity_id}|{target.entity_id}|{kind}".encode()).hexdigest()[:16],tenant_id,source.entity_id,target.entity_id,kind,confidence,evidence)
