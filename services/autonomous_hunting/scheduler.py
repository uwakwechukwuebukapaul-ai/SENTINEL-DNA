class HuntingScheduler:
 def __init__(self): self.schedules=[]
 def add(self,organization_id,expression,hypothesis_id): self.schedules.append({"organization_id":organization_id,"expression":expression,"hypothesis_id":hypothesis_id})
