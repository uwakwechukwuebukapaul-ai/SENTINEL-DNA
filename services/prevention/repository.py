class PreventionRepository:
 def __init__(self): self.recommendations=[]; self.actions=[]; self.outcomes=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
