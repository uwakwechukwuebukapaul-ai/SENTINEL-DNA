class UebaRepository:
    def __init__(self): self.profiles=[]; self.entities=[]; self.anomalies=[]; self.risks=[]
    def scoped(self, items, org): return [x for x in items if x.organization_id == org]
