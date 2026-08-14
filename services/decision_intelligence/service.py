from datetime import datetime,timezone
from uuid import uuid4
class DecisionIntelligenceService:
 def __init__(self): self.decisions=[]
 def decide(self,org,data):
  risk=float(data.get("risk_score",50)); impact=float(data.get("business_impact",50)); score=round((risk+impact)/2,2); actions=[{"action":"containment","rank":1,"reason":"Reduces immediate exposure","requires_approval":True},{"action":"monitoring","rank":2,"reason":"Preserves service availability","requires_approval":False}]; x={"id":str(uuid4()),"organization_id":org,"decision":"Human-approved containment recommended" if score>=65 else "Continue monitoring and collect evidence","confidence":round(float(data.get("confidence",.8)),2),"risk_score":risk,"impact_score":impact,"reasoning_chain":["Context fused from security signals","Risk compared with business impact","Alternatives ranked by safety and effectiveness"],"evidence":data.get("evidence",[]),"recommended_actions":actions,"alternatives":["Contain affected identity","Increase monitoring","Request analyst review"],"human_approval_required":score>=65,"created_at":datetime.now(timezone.utc).isoformat()}; self.decisions.append(x); return x
 def scoped(self,org): return [x for x in self.decisions if x["organization_id"]==org]
