class SecurityTwinRepository:
 def __init__(self): self.assets=[]; self.relationships=[]; self.paths=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
