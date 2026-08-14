from datetime import datetime,timezone
from uuid import uuid4
class LabManager:
 def __init__(self): self.environments={}; self.runs=[]
 def create(self,org):
  x={"id":str(uuid4()),"organization_id":org,"name":"Customer Zero Lab","status":"READY","synthetic":True,"created_at":datetime.now(timezone.utc).isoformat()}; self.environments[x["id"]]=x; return x
 def status(self,org): return {"environments":[x for x in self.environments.values() if x["organization_id"]==org],"runs":[x for x in self.runs if x["organization_id"]==org],"isolated":True}
