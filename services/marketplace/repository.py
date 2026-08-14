class MarketplaceRepository:
 def __init__(self): self.packages=[]; self.installations=[]; self.ratings=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
