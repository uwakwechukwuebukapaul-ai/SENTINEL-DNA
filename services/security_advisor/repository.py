class AdvisorRepository:
 def __init__(self): self.postures=[]; self.risks=[]; self.recommendations=[]; self.reports=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
