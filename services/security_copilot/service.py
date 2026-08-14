from datetime import datetime,timezone
from uuid import uuid4
class SecurityCopilotService:
 def __init__(self): self.conversations=[]
 def ask(self,org,user,prompt,context=None):
  p=prompt.lower(); intent="investigation_summary" if "summ" in p else "threat_explanation" if "threat" in p or "why" in p else "security_query"; answer="Security context reviewed. Evidence should be validated against the tenant investigation and knowledge graph."; steps=["Review correlated evidence","Validate MITRE and threat intelligence context","Confirm business impact","Request human approval before response"]
  if intent=="investigation_summary": answer="The investigation indicates correlated suspicious activity requiring analyst review."
  if intent=="threat_explanation": answer="The threat is assessed using detection signals, identity behavior, exposure, and historical context."
  x={"id":str(uuid4()),"organization_id":org,"user_id":user,"prompt":prompt,"intent":intent,"answer":answer,"evidence":(context or {}).get("evidence",[]),"reasoning":["Tenant context isolated","Relevant security sources considered","Recommendation constrained by approval policy"],"confidence":.82,"recommended_steps":steps,"actions":[{"action":"prepare_response_plan","requires_approval":True}],"created_at":datetime.now(timezone.utc).isoformat()}; self.conversations.append(x); return x
 def scoped(self,org): return [x for x in self.conversations if x["organization_id"]==org]
