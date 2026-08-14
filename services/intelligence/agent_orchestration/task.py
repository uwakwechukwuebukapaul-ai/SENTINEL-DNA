from .models import AgentTask
class AgentTaskManager:
 def run(self,task,agent,context): task.status="running"; task.result=agent.analyze(context); task.status="completed"; return task
