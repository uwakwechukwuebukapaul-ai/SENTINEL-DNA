from .models import WorkflowContext
from .router import AdaptiveWorkflowRouter
class AdaptiveWorkflowEngine:
 def __init__(self): self.router=AdaptiveWorkflowRouter()
 def create(self,case_id,**signals):
  plan=self.router.recommend(**signals); return WorkflowContext(case_id,recommended_agents=plan["agents"],approval_required=plan["approval_required"],**{k:v for k,v in signals.items() if k in {"severity","threat_type","asset_criticality","mitre_techniques","attack_path_risk"}})
