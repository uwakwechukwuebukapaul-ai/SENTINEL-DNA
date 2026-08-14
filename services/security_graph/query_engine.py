class GraphQueryEngine:
 def __init__(self,repository): self.repository=repository
 def find_related_entities(self,entity_id,tenant_id=None):
  out=[]
  for r in self.repository.find_neighbors(entity_id,tenant_id): out.append(self.repository.get_entity(r.target_entity_id if r.source_entity_id==entity_id else r.source_entity_id,tenant_id))
  return [x for x in out if x]
 def get_attack_path(self,start,end,tenant_id=None):
  path=[start]; current=start
  for _ in range(10):
   if current==end:return path
   neighbors=self.find_related_entities(current,tenant_id)
   if not neighbors:break
   current=neighbors[0].entity_id; path.append(current)
  return path if path[-1]==end else []
 def get_entity_context(self,entity_id,tenant_id=None): return {"entity":self.repository.get_entity(entity_id,tenant_id),"relationships":self.repository.find_neighbors(entity_id,tenant_id)}
 def get_campaign_context(self,entity_id,tenant_id=None): return [x for x in self.find_related_entities(entity_id,tenant_id) if x.entity_type=="campaign"]
