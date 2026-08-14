from .models import AgentExecutionSummary
class AgentWorkflowEngine:
 def __init__(self,registry): self.registry=registry
 def execute(self,case_id,context,capabilities):
  done=[]; failed=[]
  for capability in capabilities:
   agents=self.registry.discover_agents(capability,getattr(context,"tenant_id","default")); (done if agents else failed).append(agents[0].agent_id if agents else capability)
  return AgentExecutionSummary(done,failed,0,0.0)
