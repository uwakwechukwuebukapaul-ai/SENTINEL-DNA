from datetime import datetime,timezone
from uuid import uuid4
class GovernanceService:
 def __init__(self): self.controls=[]; self.evidence=[]; self.exceptions=[]
 def add_control(self,org,data):
  x={"id":str(uuid4()),"organization_id":org,"framework":data.get("framework","NIST_CSF"),"control_id":data.get("control_id",""),"name":data.get("name",""),"status":data.get("status","NOT_STARTED"),"effectiveness":float(data.get("effectiveness",0))}; self.controls.append(x); return x
 def score(self,org):
  c=[x for x in self.controls if x["organization_id"]==org]; return {"score":round(sum(x["effectiveness"] for x in c)/len(c),2) if c else 0,"controls":len(c),"implemented":sum(x["status"] in ("IMPLEMENTED","EFFECTIVE") for x in c)}
 def add_evidence(self,org,data):
  x={"id":str(uuid4()),"organization_id":org,"control_id":data.get("control_id",""),"description":data.get("description",""),"synthetic":True,"created_at":datetime.now(timezone.utc).isoformat()}; self.evidence.append(x); return x
 def report(self,org): return {"posture":self.score(org),"controls":[x for x in self.controls if x["organization_id"]==org],"evidence":[x for x in self.evidence if x["organization_id"]==org],"exceptions":[x for x in self.exceptions if x["organization_id"]==org]}
