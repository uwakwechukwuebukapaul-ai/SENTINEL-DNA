from .rules import WORKFLOW_RULES
class AdaptiveWorkflowRouter:
 def recommend(self,severity="unknown",threat_type="",asset_criticality="medium",mitre_techniques=None,attack_path_risk=0):
  key=str(threat_type).lower().replace(" ","_"); agents=list(WORKFLOW_RULES.get(key,["evidence_agent","reasoning_agent","reporting_agent"]))
  if severity in {"critical","high"} or attack_path_risk>=70: agents.insert(-1,"hunting_agent") if "hunting_agent" not in agents else None
  return {"agents":list(dict.fromkeys(agents)),"priority":"high" if severity in {"critical","high"} or attack_path_risk>=70 else "normal","approval_required":False}
