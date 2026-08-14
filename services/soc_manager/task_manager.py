from .models import SOCTask
class TaskManager:
 def __init__(self,repository): self.repository=repository
 def create(self,org,data): x=SOCTask(org,data.get("task_type","INVESTIGATE_ALERT"),data.get("priority","P3")); self.repository.tasks.append(x); return x
