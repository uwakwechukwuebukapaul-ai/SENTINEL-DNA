from datetime import datetime,timezone
from uuid import uuid4
class PilotSimulationService:
 def __init__(self): self.tenants={}; self.runs=[]
 def onboard(self,org,name="Enterprise Pilot"):
  x={"id":str(uuid4()),"organization_id":org,"name":name,"synthetic":True,"status":"ONBOARDED","users":[{"role":"SOC_ANALYST","name":"Demo Analyst"},{"role":"CISO","name":"Demo CISO"}],"assets":[{"name":"Finance Database","criticality":"CRITICAL"},{"name":"Corporate Laptop","criticality":"HIGH"}],"policies":["MFA required","Privileged access review"],"detection_rules":["Suspicious login","Ransomware behavior"],"threat_feeds":["Synthetic ATT&CK feed"],"investigation_history":[],"created_at":datetime.now(timezone.utc).isoformat()}; self.tenants[org]=x; return x
 def run(self,org,scenario):
  if org not in self.tenants:self.onboard(org)
  x={"id":str(uuid4()),"organization_id":org,"scenario":scenario,"synthetic":True,"incident_state":"RESOLVED","detection":"TRIGGERED","investigation":"COMPLETED","executive_summary":"Synthetic pilot scenario completed","created_at":datetime.now(timezone.utc).isoformat()}; self.runs.append(x); self.tenants[org]["investigation_history"].append(x); return x
 def view(self,org,mode): return {"mode":mode,"tenant":self.tenants.get(org),"runs":[x for x in self.runs if x["organization_id"]==org],"synthetic_only":True}
