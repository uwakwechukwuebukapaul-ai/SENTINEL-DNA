from datetime import datetime,timezone
from uuid import uuid4
class IdentitySecurityService:
 def __init__(self): self.identities=[]; self.relationships=[]; self.reviews=[]
 def add(self,org,data):
  x={"id":str(uuid4()),"organization_id":org,"name":data.get("name",""),"identity_type":data.get("identity_type","USER"),"roles":data.get("roles",[]),"privileges":data.get("privileges",[]),"risk_score":0,"synthetic":True,"created_at":datetime.now(timezone.utc).isoformat()}; self.identities.append(x); return x
 def risk(self,identity):
  score=min(100,len(identity["privileges"])*15+(30 if "admin" in [x.lower() for x in identity["roles"]] else 0)); identity["risk_score"]=score; return {"identity_id":identity["id"],"score":score,"severity":"CRITICAL" if score>=85 else "HIGH" if score>=65 else "MEDIUM" if score>=35 else "LOW","indicators":["privileged account" if score>=65 else "baseline review"]}
 def review(self,org,identity_id):
  x={"id":str(uuid4()),"organization_id":org,"identity_id":identity_id,"status":"PENDING","synthetic":True}; self.reviews.append(x); return x
 def scoped(self,org): return [x for x in self.identities if x["organization_id"]==org]
