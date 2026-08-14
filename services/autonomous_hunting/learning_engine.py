class LearningEngine:
 def __init__(self): self.outcomes=[]
 def record(self,organization_id,outcome,metadata=None): self.outcomes.append({"organization_id":organization_id,"outcome":outcome,"metadata":metadata or {}})
