class HuntingRepository:
 def __init__(self): self.hypotheses=[]; self.executions=[]; self.findings=[]; self.detections=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
