class AgentRouter:
 def route(self,task_type,agents):
  terms={"INVESTIGATE_ALERT":"investigation","RUN_HUNT":"hunt","ENRICH_INTELLIGENCE":"intelligence","ANALYZE_RISK":"risk","CREATE_DETECTION":"detection","EXECUTE_RESPONSE":"response"}; term=terms.get(task_type,"investigation"); return next((a for a in agents if any(term in str(c).lower() for c in a.capabilities) and a.availability=="AVAILABLE"),agents[0] if agents else None)
