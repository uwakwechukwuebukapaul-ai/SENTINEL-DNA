class GraphRepository:
    def __init__(self): self.nodes=[]; self.relationships=[]
    def scoped(self, items, org): return [x for x in items if x.organization_id==org]
