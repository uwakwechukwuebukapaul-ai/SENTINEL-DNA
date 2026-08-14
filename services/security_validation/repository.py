class ValidationRepository:
 def __init__(self): self.scenarios=[]; self.executions=[]; self.results=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
