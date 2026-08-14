class AttackPathEngine:
 def __init__(self,repository): self.repository=repository
 def find_paths(self,start_entity,tenant_id=None,max_depth=5):
  paths=[]
  def walk(current,path):
   if len(path)>max_depth:return
   for r in self.repository.find_neighbors(current,tenant_id):
    nxt=r.target_entity_id if r.source_entity_id==current else r.source_entity_id
    if nxt in path:continue
    new=path+[nxt]; paths.append(new); walk(nxt,new)
  walk(start_entity,[start_entity]); return paths
 def find_attack_routes(self,start_entity,destination_type,tenant_id=None): return [p for p in self.find_paths(start_entity,tenant_id) if (e:=self.repository.get_entity(p[-1],tenant_id)) and e.entity_type==destination_type]
 def identify_high_risk_paths(self,start_entity,tenant_id=None): return [p for p in self.find_paths(start_entity,tenant_id) if len(p)>=3]
 def get_entity_attack_surface(self,entity_id,tenant_id=None): return self.find_paths(entity_id,tenant_id)
