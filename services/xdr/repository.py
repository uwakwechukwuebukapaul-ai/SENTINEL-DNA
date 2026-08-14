class XDRRepository:
 def __init__(self): self.signals=[]; self.incidents=[]; self.stories=[]
 def scoped(self,items,org): return [x for x in items if x.organization_id==org]
 def add_signal(self,x): self.signals.append(x); return x
 def add_incident(self,x): self.incidents.append(x); return x
