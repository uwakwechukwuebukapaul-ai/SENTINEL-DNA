class ValidationScheduler:
 def __init__(self): self.schedules=[]
 def add(self,organization_id,scenario_id,expression): self.schedules.append({"organization_id":organization_id,"scenario_id":scenario_id,"expression":expression})
