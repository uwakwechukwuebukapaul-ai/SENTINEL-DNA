from .models import SOCDecision
from .priority_engine import PriorityEngine
from .agent_router import AgentRouter
class SOCSupervisor:
 def __init__(self,repository): self.repository=repository; self.priority=PriorityEngine(); self.router=AgentRouter()
 def evaluate(self,org,data):
  priority=self.priority.calculate(data); task_type=data.get("task_type","INVESTIGATE_ALERT"); agents=self.repository.scoped(self.repository.agents,org); agent=self.router.route(task_type,agents); decision=SOCDecision(org,"TASK_ASSIGNMENT","Priority %s routed to specialized agent"%priority,.85); self.repository.decisions.append(decision); return {"priority":priority,"agent":agent.public() if agent else None,"decision":decision.public()}
