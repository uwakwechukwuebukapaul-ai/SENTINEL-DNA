from dataclasses import asdict,dataclass,field
@dataclass
class BlastRadiusReport:
 entity_id:str; impacted_entities:list[str]=field(default_factory=list); impacted_types:dict[str,int]=field(default_factory=dict); score:int=0
 def to_dict(self): return asdict(self)
class BlastRadiusAnalyzer:
 def __init__(self,repository): self.repository=repository
 def analyze(self,entity_id,tenant_id=None):
  related=[r.target_entity_id if r.source_entity_id==entity_id else r.source_entity_id for r in self.repository.find_neighbors(entity_id,tenant_id)]; types={}
  for i in related:
   e=self.repository.get_entity(i,tenant_id)
   if e: types[e.entity_type]=types.get(e.entity_type,0)+1
  return BlastRadiusReport(entity_id,related,types,min(100,len(related)*10))
