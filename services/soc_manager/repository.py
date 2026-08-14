class SOCRepository:
 def __init__(self): self.tasks=[]; self.agents=[]; self.decisions=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
