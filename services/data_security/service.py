from datetime import datetime,timezone
from uuid import uuid4
class DataSecurityService:
 def __init__(self): self.assets=[]; self.access=[]; self.policies=[]
 def add_asset(self,org,data):
  x={"id":str(uuid4()),"organization_id":org,"name":data.get("name",""),"asset_type":data.get("asset_type","DATABASE"),"classification":data.get("classification","INTERNAL"),"owner":data.get("owner",""),"risk_score":0,"synthetic":True,"created_at":datetime.now(timezone.utc).isoformat()}; self.assets.append(x); return x
 def risk(self,x):
  score={"PUBLIC":10,"INTERNAL":35,"CONFIDENTIAL":65,"RESTRICTED":90}.get(x["classification"].upper(),35)+min(10,len([a for a in self.access if a["asset_id"]==x["id"]])*3); x["risk_score"]=min(100,score); return {"asset_id":x["id"],"score":x["risk_score"],"severity":"CRITICAL" if x["risk_score"]>=85 else "HIGH" if x["risk_score"]>=65 else "MEDIUM"}
 def add_access(self,org,data):
  x={"id":str(uuid4()),"organization_id":org,"asset_id":data.get("asset_id",""),"identity_id":data.get("identity_id",""),"access_type":data.get("access_type","READ"),"synthetic":True}; self.access.append(x); return x
 def scoped(self,org): return [x for x in self.assets if x["organization_id"]==org]
