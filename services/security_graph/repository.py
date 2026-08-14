class SecurityGraphRepository:
 def __init__(self): self.entities={}; self.relationships={}
 def add_entity(self,e): self.entities.setdefault((e.tenant_id,e.entity_id),e); return self.entities[(e.tenant_id,e.entity_id)]
 def get_entity(self,i,tenant_id=None): return next((e for (t,x),e in self.entities.items() if x==i and (tenant_id is None or t==tenant_id)),None)
 def list_entities(self,tenant_id=None): return [e for (t,_),e in self.entities.items() if tenant_id is None or t==tenant_id]
 def add_relationship(self,r): self.relationships.setdefault((r.tenant_id,r.source_entity_id,r.target_entity_id,r.relationship_type),r); return r
 def get_relationships(self,tenant_id=None): return [r for (t,_,_,_),r in self.relationships.items() if tenant_id is None or t==tenant_id]
 def find_neighbors(self,i,tenant_id=None): return [r for r in self.get_relationships(tenant_id) if r.source_entity_id==i or r.target_entity_id==i]
 def remove_entity(self,i,tenant_id=None):
  e=self.get_entity(i,tenant_id); return self.entities.pop((e.tenant_id,e.entity_id),None) is not None if e else False
