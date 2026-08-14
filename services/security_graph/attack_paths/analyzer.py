import hashlib
from .models import AttackPath,AttackPathNode
from .exposure import ExposureAnalyzer
class AttackPathAnalyzer:
 def __init__(self,repository): self.repository=repository; self.exposure=ExposureAnalyzer()
 def analyze(self,tenant_id,path):
  entities=[self.repository.get_entity(i,tenant_id) for i in path]; entities=[e for e in entities if e]; nodes=[AttackPathNode(e.entity_id,e.entity_type,"source" if i==0 else "destination" if i==len(entities)-1 else "intermediate",e.metadata.get("exposure_level","unknown")) for i,e in enumerate(entities)]; score=self.exposure.calculate(external_exposure=any(e.metadata.get("internet_exposed",False) for e in entities)).exposure_score; pid="PATH-"+hashlib.sha256((tenant_id+"|"+"|".join(path)).encode()).hexdigest()[:16]; return AttackPath(pid,tenant_id,"Detected attack route","high" if score>70 else "medium",.8,nodes,[],score,"A relationship chain connects exposed or vulnerable entities to a potentially impacted resource.")
